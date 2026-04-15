from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import APIRouter
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.core.base_schema import CommonIds, Success, SuccessExtra
from app.core.crud import CRUDBase
from app.core.sqids import encode_id
from app.core.types import SqidPath


@dataclass
class SearchFieldConfig:
    """搜索字段配置，用于自动构建 Q 查询。

    ``range_fields`` 约定：对列表中的 ``"created_at"``，schema 需包含
    ``created_at_start``（映射为 ``created_at__gte``）和
    ``created_at_end``（映射为 ``created_at__lte``），两者均为可选字段。
    """

    contains_fields: list[str] = field(default_factory=list)
    icontains_fields: list[str] = field(default_factory=list)
    exact_fields: list[str] = field(default_factory=list)
    iexact_fields: list[str] = field(default_factory=list)
    in_fields: list[str] = field(default_factory=list)
    range_fields: list[str] = field(default_factory=list)


# 所有标准路由的名称（顺序即注册顺序）
_ALL_ROUTES = ("list", "get", "create", "update", "delete", "batch_delete")


class _OrderedRouter(APIRouter):
    """保持静态路由排在参数化路由前面的 APIRouter。

    防止 ``GET /resources/{item_id}`` 遮蔽后续添加的静态路由（如
    ``GET /resources/pages``）。每次调用 ``add_api_route`` 后都会对路由列表
    重新排序，使不含 ``{…}`` 的路径排在前面（Python 的稳定排序会保留
    同组内的相对顺序）。
    """

    def add_api_route(self, path: str, *args, **kwargs) -> None:  # type: ignore[override]
        super().add_api_route(path, *args, **kwargs)
        self.routes.sort(key=lambda r: 1 if isinstance(r, APIRoute) and "{" in r.path else 0)


class CRUDRouter:
    """
    CRUD Router 工厂，自动生成标准 CRUD 接口。

    统一路由风格（参见 ``CLAUDE.md`` 的 "API Conventions"）::

        POST   /resources/search     列表/搜索 (Body: list_schema, 含 current/size)
        GET    /resources/{item_id}  详情
        POST   /resources            创建
        PATCH  /resources/{item_id}  更新
        DELETE /resources/{item_id}  删除
        DELETE /resources            批量删除 (Body: {ids: [...]})

    基础用法::

        crud = CRUDRouter(
            prefix="/roles",
            controller=role_controller,
            create_schema=RoleCreate,
            update_schema=RoleUpdate,
            list_schema=RoleSearch,
            search_fields=SearchFieldConfig(
                contains_fields=["role_name", "role_code"],
                exact_fields=["status_type"],
            ),
            summary_prefix="角色",
        )
        router = crud.router

    自定义某一路由时使用 ``@crud.override("name")`` 装饰器 — 该装饰器会移除
    CRUDRouter 默认注册的实现，并用你的函数替换，同时保留路径/方法/summary::

        crud = CRUDRouter(prefix="/users", controller=user_controller, ...)

        @crud.override("create")
        async def create_user(user_in: UserCreate, request: Request):
            # 自定义逻辑 — 事务、密码哈希、角色关联等
            return Success(...)

        router = crud.router

    完全关闭某个路由用 ``enable_routes``::

        crud = CRUDRouter(..., enable_routes={"get", "delete"})

    额外的业务接口继续在 ``crud.router`` 上挂载即可::

        @crud.router.post("/roles/{role_id}/menus")
        async def get_role_menus(role_id: int): ...
    """

    def __init__(
        self,
        prefix: str,
        controller: CRUDBase,
        create_schema: type[BaseModel] | None = None,
        update_schema: type[BaseModel] | None = None,
        list_schema: type[BaseModel] | None = None,
        search_fields: SearchFieldConfig | None = None,
        summary_prefix: str = "",
        list_order: list[str] | None = None,
        exclude_fields: list[str] | None = None,
        enable_routes: set[str] | None = None,
        record_transform: Callable | None = None,
        soft_delete: bool = False,
        tree_endpoint: bool = False,
    ):
        """
        Args:
            prefix: 路由前缀，如 "/roles"。
            controller: CRUDBase 控制器实例。
            create_schema: 创建 schema。
            update_schema: 更新 schema。
            list_schema: 列表搜索 schema（必须继承 PageQueryBase 或含 current/size 字段）。
            search_fields: 搜索字段配置。
            summary_prefix: 接口 summary 前缀，如 "角色"。
            list_order: 列表排序字段，默认 ["id"]。
            exclude_fields: to_dict 时排除的字段。
            enable_routes: 启用的路由集合，默认全部启用。可选值:
                list, get, create, update, delete, batch_delete。
            record_transform: 自定义记录转换函数，签名:
                ``async def transform(obj) -> dict``。
            soft_delete: 为 True 时删除/批量删除路由使用
                ``controller.soft_remove()`` / ``controller.soft_batch_remove()``
                而非物理删除。需要模型使用 ``SoftDeleteMixin``。
            tree_endpoint: 为 True 时自动生成 ``GET /{resource}/tree`` 树形接口。
                需要模型使用 ``TreeMixin``（包含 ``parent_id`` 字段）。
        """
        self.prefix = prefix
        self.controller = controller
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.list_schema = list_schema
        self.search_fields = search_fields or SearchFieldConfig()
        self.summary_prefix = summary_prefix
        self.list_order = list_order or ["id"]
        self.exclude_fields = exclude_fields or []
        self.record_transform = record_transform
        self.soft_delete = soft_delete
        self.tree_endpoint = tree_endpoint

        # 资源名（从 prefix 提取，如 "/roles" → "roles"）
        self._resource = prefix.strip("/").split("/")[-1]

        self.enable_routes: set[str] = enable_routes if enable_routes is not None else set(_ALL_ROUTES)

        # 存储每个标准路由的规格：name -> {"path", "methods", "summary"}
        # override() 根据 name 找到对应规格，再用用户函数替换默认实现
        self._route_specs: dict[str, dict] = {}

        self.router = _OrderedRouter()
        self._register_routes()
        if self.tree_endpoint:
            self._add_tree_route()

    # ---- 路由注册入口 ----

    def _register_routes(self):
        if "list" in self.enable_routes:
            self._add_list_route()
        if "get" in self.enable_routes:
            self._add_get_route()
        if "create" in self.enable_routes:
            self._add_create_route()
        if "update" in self.enable_routes:
            self._add_update_route()
        if "delete" in self.enable_routes:
            self._add_delete_route()
        if "batch_delete" in self.enable_routes:
            self._add_batch_delete_route()

    async def _to_record(self, obj) -> dict:
        if self.record_transform:
            return await self.record_transform(obj)
        return await obj.to_dict(exclude_fields=self.exclude_fields)

    # ---- override 钩子 ----

    def get_route_info(self, name: str) -> dict:
        """获取指定标准路由的元信息，便于 override 时参考参数签名。

        返回包含 path、methods、summary、signature 的字典::

            >>> crud.get_route_info("list")
            {
                "path": "/roles/search",
                "methods": {"POST"},
                "summary": "查看角色列表",
                "signature": "async def list_items(obj_in: RoleSearch) -> SuccessExtra"
            }

        Raises:
            ValueError: 路由名不存在或未启用。
        """
        if name not in self._route_specs:
            raise ValueError(f"Route '{name}' is not enabled or does not exist. Available: {sorted(self._route_specs.keys())}")
        spec = dict(self._route_specs[name])
        signatures = {
            "list": f"async def list_items(obj_in: {self.list_schema.__name__})" if self.list_schema else "async def list_items()",
            "get": "async def get_item(item_id: SqidPath)",
            "create": f"async def create_item(obj_in: {self.create_schema.__name__})" if self.create_schema else "async def create_item()",
            "update": f"async def update_item(item_id: SqidPath, obj_in: {self.update_schema.__name__})" if self.update_schema else "async def update_item(item_id: SqidPath)",
            "delete": "async def delete_item(item_id: SqidPath)",
            "batch_delete": "async def batch_delete(obj_in: CommonIds)",
        }
        spec["signature"] = signatures.get(name, "")
        return spec

    def override(self, name: str) -> Callable:
        """装饰器: 用用户实现替换指定标准路由的默认实现。

        ``name`` 必须是已注册的路由名 (``list`` / ``get`` / ``create`` / ``update`` /
        ``delete`` / ``batch_delete``)，且该路由在 ``enable_routes`` 中启用。

        替换后仍保留 CRUDRouter 生成的 path / method / summary，用户只需提供
        函数体和参数签名。

        各路由的标准参数签名（可通过 ``crud.get_route_info(name)`` 查看）::

            list:         async def list_items(obj_in: <list_schema>)
            get:          async def get_item(item_id: int)
            create:       async def create_item(obj_in: <create_schema>)
            update:       async def update_item(item_id: int, obj_in: <update_schema>)
            delete:       async def delete_item(item_id: int)
            batch_delete: async def batch_delete(obj_in: CommonIds)
        """
        if name not in self._route_specs:
            raise ValueError(f"Cannot override '{name}': route is not enabled or does not exist. Available: {sorted(self._route_specs.keys())}")
        spec = self._route_specs[name]

        def decorator(func: Callable) -> Callable:
            self._remove_route(spec["path"], spec["methods"])
            self.router.add_api_route(
                spec["path"],
                func,
                methods=list(spec["methods"]),
                summary=spec["summary"],
            )
            return func

        return decorator

    def _remove_route(self, path: str, methods: set[str]) -> None:
        """从 router.routes 中移除匹配 (path, methods) 的默认路由。"""
        self.router.routes = [r for r in self.router.routes if not (isinstance(r, APIRoute) and r.path == path and set(r.methods) == methods)]

    def _register_spec(self, name: str, path: str, methods: set[str], summary: str, endpoint: Callable) -> None:
        """登记路由规格并将其挂载到 router 上。"""
        self._route_specs[name] = {"path": path, "methods": methods, "summary": summary}
        self.router.add_api_route(path, endpoint, methods=list(methods), summary=summary)

    # ---- 标准路由实现 ----

    def _add_list_route(self):
        if not self.list_schema:
            return

        controller = self.controller
        search_fields = self.search_fields
        list_order = self.list_order
        to_record = self._to_record
        schema = self.list_schema

        async def list_items(obj_in: schema):  # type: ignore[valid-type]
            q = controller.build_search(
                obj_in,
                contains_fields=search_fields.contains_fields,
                icontains_fields=search_fields.icontains_fields,
                exact_fields=search_fields.exact_fields,
                iexact_fields=search_fields.iexact_fields,
                in_fields=search_fields.in_fields,
                range_fields=search_fields.range_fields,
            )
            current = getattr(obj_in, "current", 1)
            size = getattr(obj_in, "size", 10)
            order = getattr(obj_in, "order_by", None) or list_order
            total, objs = await controller.list(page=current, page_size=size, search=q, order=order)
            records = [await to_record(obj) for obj in objs]
            return SuccessExtra(data={"records": records}, total=total, current=current, size=size)

        self._register_spec(
            "list",
            f"/{self._resource}/search",
            {"POST"},
            f"查看{self.summary_prefix}列表",
            list_items,
        )

    def _add_get_route(self):
        controller = self.controller
        to_record = self._to_record

        async def get_item(item_id: SqidPath):
            obj = await controller.get(id=item_id)
            return Success(data=await to_record(obj))

        self._register_spec(
            "get",
            f"/{self._resource}/{{item_id}}",
            {"GET"},
            f"查看{self.summary_prefix}",
            get_item,
        )

    def _add_create_route(self):
        if not self.create_schema:
            return

        controller = self.controller
        schema = self.create_schema

        async def create_item(obj_in: schema):  # type: ignore[valid-type]
            new_obj = await controller.create(obj_in=obj_in)
            return Success(msg="创建成功", data={"createdId": encode_id(new_obj.id)})

        self._register_spec(
            "create",
            f"/{self._resource}",
            {"POST"},
            f"创建{self.summary_prefix}",
            create_item,
        )

    def _add_update_route(self):
        if not self.update_schema:
            return

        controller = self.controller
        schema = self.update_schema

        async def update_item(item_id: SqidPath, obj_in: schema):  # type: ignore[valid-type]
            await controller.update(id=item_id, obj_in=obj_in)
            return Success(msg="更新成功", data={"updatedId": encode_id(item_id)})

        self._register_spec(
            "update",
            f"/{self._resource}/{{item_id}}",
            {"PATCH"},
            f"更新{self.summary_prefix}",
            update_item,
        )

    def _add_delete_route(self):
        controller = self.controller
        use_soft = self.soft_delete

        async def delete_item(item_id: SqidPath):
            if use_soft:
                await controller.soft_remove(id=item_id)
            else:
                await controller.remove(id=item_id)
            return Success(msg="删除成功", data={"deletedId": encode_id(item_id)})

        self._register_spec(
            "delete",
            f"/{self._resource}/{{item_id}}",
            {"DELETE"},
            f"删除{self.summary_prefix}",
            delete_item,
        )

    def _add_batch_delete_route(self):
        controller = self.controller
        use_soft = self.soft_delete

        async def batch_delete(obj_in: CommonIds):
            if use_soft:
                deleted_count = await controller.soft_batch_remove(obj_in.ids)
            else:
                deleted_count = await controller.batch_remove(obj_in.ids)
            return Success(msg="删除成功", data={"deletedCount": deleted_count, "deletedIds": [encode_id(i) for i in obj_in.ids]})

        self._register_spec(
            "batch_delete",
            f"/{self._resource}",
            {"DELETE"},
            f"批量删除{self.summary_prefix}",
            batch_delete,
        )

    # ---- 树形端点 ----

    def _add_tree_route(self):
        """注册 ``GET /{resource}/tree``，返回嵌套树结构。

        需要模型含 ``parent_id`` 字段（``TreeMixin``）。
        """
        controller = self.controller
        to_record = self._to_record
        summary_prefix = self.summary_prefix

        async def get_tree():
            nodes = await controller.get_tree()
            records = [await to_record(node) for node in nodes]
            return Success(data=_build_nested_tree(records))

        self.router.add_api_route(
            f"/{self._resource}/tree",
            get_tree,
            methods=["GET"],
            summary=f"查看{summary_prefix}树",
        )


def _build_nested_tree(
    records: list[dict],
    parent_id_key: str = "parentId",
    root_value: int = 0,
) -> list[dict]:
    """将扁平 dict 列表组装为嵌套树结构。

    每个 dict 需包含 ``id`` 和 ``parentId``（camelCase，来自 ``to_dict()``）。

    Args:
        records: ``to_dict()`` 产出的字典列表。
        parent_id_key: 字典中父节点 ID 的键名（默认 camelCase ``parentId``）。
        root_value: 顶级节点的 parent_id 值（默认 0）。
    """
    tree: list[dict] = []
    for record in records:
        if record.get(parent_id_key, root_value) == root_value:
            children = _build_nested_tree(records, parent_id_key, record["id"])
            if children:
                record["children"] = children
            tree.append(record)
    return tree
