from typing import Any, Generic, NewType, TypeVar

from pydantic import BaseModel
from tortoise.expressions import Q
from tortoise.functions import Count
from tortoise.models import Model
from tortoise.transactions import in_transaction

from app.core.ctx import CTX_USER_ID

Total = NewType("Total", int)
ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

_list = list  # 避免与 CRUDBase.list 方法名冲突


def get_db_conn(model: type[Model]) -> str:
    """返回模型所配置的 Tortoise 连接名称。

    在事务中优先使用本函数，避免硬编码连接名：

        async with in_transaction(get_db_conn(User)):
            ...
    """
    return model._meta.default_connection or "default"


def _get_current_user() -> str | None:
    user_id = CTX_USER_ID.get()
    return str(user_id) if user_id is not None else None


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, *args: Q, **kwargs) -> ModelType:
        return await self.model.get(*args, **kwargs)

    async def get_or_none(self, *args: Q, **kwargs) -> ModelType | None:
        return await self.model.filter(*args, **kwargs).first()

    async def exists(self, *args: Q, **kwargs) -> bool:
        return await self.model.filter(*args, **kwargs).exists()

    async def count(self, search: Q = Q()) -> int:
        return await self.model.filter(search).count()

    async def list(
        self,
        page: int | None,
        page_size: int | None,
        search: Q = Q(),
        order: _list[str] | None = None,
        fields: _list[str] | None = None,
        last_id: int | None = None,
        count_by_pk_field: bool = False,
        select_related: _list[str] | None = None,
        prefetch_related: _list[str] | None = None,
    ) -> tuple[Total, _list[ModelType]]:
        order = order or []
        page = page or 1
        page_size = page_size or 10

        query = self.model.filter(search).distinct()
        if last_id:
            query = query.filter(id__gt=last_id)

        if fields:
            query = query.only(*fields)

        if select_related:
            query = query.select_related(*select_related)

        if count_by_pk_field:
            pk_attr = self.model._meta.pk_attr
            result = await query.annotate(distinct_count=Count(pk_attr, distinct=True)).values("distinct_count")
            total = result[0]["distinct_count"] if result else 0
        else:
            total = await query.count()

        if last_id:
            query = query.order_by(*order).limit(page_size)
        else:
            query = query.offset((page - 1) * page_size).limit(page_size).order_by(*order)

        if prefetch_related:
            query = query.prefetch_related(*prefetch_related)

        result = await query

        return Total(total), result

    async def create(self, obj_in: CreateSchemaType, exclude: set[str] | None = None) -> ModelType:
        if isinstance(obj_in, dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude_none=True, exclude=exclude)
        if "created_by" in self.model._meta.db_fields:
            obj_dict.setdefault("created_by", _get_current_user())
        obj: ModelType = self.model(**obj_dict)
        await obj.save()
        return obj

    async def batch_create(self, obj_in_list: _list[CreateSchemaType], exclude: set[str] | None = None) -> _list[ModelType]:
        obj_dicts = []
        for obj_in in obj_in_list:
            if isinstance(obj_in, dict):
                obj_dicts.append(obj_in)
            else:
                obj_dicts.append(obj_in.model_dump(exclude_unset=True, exclude_none=True, exclude=exclude))
        objs = [self.model(**obj_dict) for obj_dict in obj_dicts]
        await self.model.bulk_create(objs)
        return objs

    async def update(self, id: int, obj_in: UpdateSchemaType | dict[str, Any], exclude: set[str] | None = None) -> ModelType:
        if isinstance(obj_in, dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude_none=True, exclude=exclude)
        if "updated_by" in self.model._meta.db_fields:
            obj_dict["updated_by"] = _get_current_user()
        async with in_transaction(get_db_conn(self.model)):
            obj = await self.get(id=id)
            obj = obj.update_from_dict(obj_dict)
            await obj.save()
        return obj

    async def batch_update(self, ids: _list[int], obj_in: UpdateSchemaType | dict[str, Any], exclude: set[str] | None = None) -> int:
        if isinstance(obj_in, dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude_none=True, exclude=exclude)
        return await self.model.filter(id__in=ids).update(**obj_dict)

    async def update_by_filter(self, search: Q, obj_in: UpdateSchemaType | dict[str, Any], exclude: set[str] | None = None) -> int:
        if isinstance(obj_in, dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude_none=True, exclude=exclude)
        return await self.model.filter(search).update(**obj_dict)

    async def remove(self, id: int) -> None:
        obj = await self.get(id=id)
        await obj.delete()

    async def batch_remove(self, ids: _list[int]) -> int:
        return await self.model.filter(id__in=ids).delete()

    async def remove_by_filter(self, search: Q) -> int:
        return await self.model.filter(search).delete()

    def build_search(
        self,
        obj_in: BaseModel,
        contains_fields: _list[str] | None = None,
        icontains_fields: _list[str] | None = None,
        exact_fields: _list[str] | None = None,
        iexact_fields: _list[str] | None = None,
        in_fields: _list[str] | None = None,
        initial: Q | None = None,
        include_fields: set[str] | None = None,
        exclude_fields: set[str] | None = None,
        extra: Q | None = None,
    ) -> Q:
        """
        从 Pydantic schema 自动构建 Tortoise Q 查询对象。

        Args:
            obj_in: Pydantic schema 实例
            contains_fields: 模糊匹配字段（大小写敏感）
            icontains_fields: 模糊匹配字段（忽略大小写）
            exact_fields: 精确匹配字段（大小写敏感）
            iexact_fields: 精确匹配字段（忽略大小写）
            in_fields: IN 查询字段（值为列表）
            initial: 初始 Q 对象
            include_fields: 仅处理指定字段（白名单），为 None 则处理所有
            exclude_fields: 排除指定字段（黑名单）
            extra: 额外的 Q 条件，会与自动构建的结果合并
        """
        q = initial or Q()
        data = obj_in.model_dump(exclude_unset=True, exclude_none=True)

        def _should_process(field_name: str) -> bool:
            if include_fields is not None and field_name not in include_fields:
                return False
            if exclude_fields is not None and field_name in exclude_fields:
                return False
            return field_name in data and data[field_name] is not None and data[field_name] != ""

        for field in contains_fields or []:
            if _should_process(field):
                q &= Q(**{f"{field}__contains": data[field]})

        for field in icontains_fields or []:
            if _should_process(field):
                q &= Q(**{f"{field}__icontains": data[field]})

        for field in exact_fields or []:
            if _should_process(field):
                q &= Q(**{field: data[field]})

        for field in iexact_fields or []:
            if _should_process(field):
                q &= Q(**{f"{field}__iexact": data[field]})

        for field in in_fields or []:
            if _should_process(field):
                q &= Q(**{f"{field}__in": data[field]})

        if extra:
            q &= extra

        return q
