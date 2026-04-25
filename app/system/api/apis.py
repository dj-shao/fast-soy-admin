from app.core.base_schema import Success, SuccessExtra
from app.core.router import CRUDRouter, SearchFieldConfig
from app.system.api.utils import generate_tags_recursive_list
from app.system.controllers import api_controller
from app.system.models import Api
from app.system.schemas.admin import ApiSearch
from app.system.services.api import build_api_tree, list_apis_with_scope

# API 资源由 refresh_api_list() 全量对账维护，UI 仅提供只读浏览能力
crud = CRUDRouter(
    prefix="/apis",
    controller=api_controller,
    list_schema=ApiSearch,
    search_fields=SearchFieldConfig(
        contains_fields=["api_path"],
        exact_fields=["summary", "status_type"],
    ),
    summary_prefix="API",
    list_order=["tags", "id"],
    exclude_fields=["created_at", "updated_at"],
    enable_routes={"list"},
)
router = crud.router


@crud.override("list")
async def _list_apis(obj_in: ApiSearch):
    total, records, current, size = await list_apis_with_scope(obj_in)
    return SuccessExtra(data={"records": records}, total=total, current=current, size=size)


# ---- 扩展：API 树 / tags ----


@router.get("/apis/tree", summary="查看API树")
async def _():
    api_objs = await Api.all()
    return Success(data=build_api_tree(api_objs) if api_objs else [])


@router.get("/apis/tags", summary="查看API tags")
async def _():
    data = await generate_tags_recursive_list()
    return Success(data=data)
