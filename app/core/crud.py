from datetime import datetime, timezone
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

    # ---- 软删除（需要模型使用 SoftDeleteMixin） ----

    async def soft_remove(self, id: int) -> None:
        """软删除：设置 ``deleted_at = now()``，不物理删除行。

        要求模型包含 ``SoftDeleteMixin``（提供 ``deleted_at`` 字段）。
        """
        obj = await self.get(id=id)
        update_fields = ["deleted_at"]
        obj.deleted_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]
        if "updated_by" in self.model._meta.db_fields:
            obj.updated_by = _get_current_user()  # type: ignore[attr-defined]
            update_fields.append("updated_by")
        await obj.save(update_fields=update_fields)

    # ---- 树形结构（需要模型使用 TreeMixin） ----

    async def get_tree(self, search: Q = Q(), order: _list[str] | None = None) -> _list[ModelType]:
        """获取所有节点（扁平列表），按 ``order`` + ``id`` 排序。

        调用方负责将扁平列表组装为嵌套树结构（参见 ``CRUDRouter._build_nested_tree``）。
        """
        return await self.model.filter(search).order_by(*(order or ["order", "id"]))

    async def get_children(self, parent_id: int, search: Q = Q()) -> _list[ModelType]:
        """获取指定父节点的直接子节点。"""
        return await self.model.filter(Q(parent_id=parent_id) & search).order_by("order", "id")

    async def soft_batch_remove(self, ids: _list[int]) -> int:
        """批量软删除。"""
        updates: dict[str, Any] = {"deleted_at": datetime.now(tz=timezone.utc)}
        if "updated_by" in self.model._meta.db_fields:
            updates["updated_by"] = _get_current_user()
        return await self.model.filter(id__in=ids).update(**updates)

    def build_search(
        self,
        obj_in: BaseModel,
        contains_fields: _list[str] | None = None,
        icontains_fields: _list[str] | None = None,
        exact_fields: _list[str] | None = None,
        iexact_fields: _list[str] | None = None,
        in_fields: _list[str] | None = None,
        range_fields: _list[str] | None = None,
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
            range_fields: 范围查询字段列表。对于 ``range_fields=["created_at"]``，
                schema 中需提供 ``created_at_start``（→ ``created_at__gte``）和
                ``created_at_end``（→ ``created_at__lte``），均为可选。
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

        for field in range_fields or []:
            start_key = f"{field}_start"
            end_key = f"{field}_end"
            if _should_process(start_key):
                q &= Q(**{f"{field}__gte": data[start_key]})
            if _should_process(end_key):
                q &= Q(**{f"{field}__lte": data[end_key]})

        if extra:
            q &= extra

        return q
