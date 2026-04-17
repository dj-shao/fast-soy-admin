from fastapi.routing import APIRoute
from loguru import logger
from tortoise.transactions import in_transaction

from app.core.crud import get_db_conn
from app.core.exceptions import IntegrityError
from app.system.models import Api
from app.system.radar.developer import radar_log


async def refresh_api_list():
    from app import fastapi_app

    app_routes = [route for route in fastapi_app.routes if isinstance(route, APIRoute)]
    app_routes_compared = [(list(route.methods)[0].lower(), route.path_format) for route in app_routes]

    async with in_transaction(get_db_conn(Api)):
        existing_apis = [(str(api.api_method.value), api.api_path) for api in await Api.all()]

        for api_method, api_path in set(existing_apis) - set(app_routes_compared):
            logger.error(f"API Deleted {api_method} {api_path}")
            radar_log("API已删除", level="WARNING", data={"method": api_method, "path": api_path})
            await Api.filter(api_method=api_method, api_path=api_path).delete()

        for route in app_routes:
            api_method = list(route.methods)[0].lower()
            api_path = route.path_format
            summary = route.summary
            tags = list(route.tags)
            instance = await Api.filter(api_path=api_path, api_method=api_method).first()
            if instance:
                await Api.filter(id=instance.id).update(summary=summary, tags=tags, is_system=True)
            else:
                try:
                    await Api.create(api_path=api_path, api_method=api_method, summary=summary, tags=tags, is_system=True)
                except IntegrityError:
                    await Api.filter(api_path=api_path, api_method=api_method).update(summary=summary, tags=tags, is_system=True)


async def generate_tags_recursive_list():
    from app import fastapi_app

    app_routes = [route for route in fastapi_app.routes if isinstance(route, APIRoute)]
    tags_list = [list(route.tags) for route in app_routes]
    unique_tags = list(set(tuple(tag) for tag in sorted(tags_list)))

    def build_tree():
        tree: list[dict] = []
        for tags in unique_tags:
            current_level = tree
            for tag in tags:
                existing_tag = next((item for item in current_level if item["value"] == tag), None)
                if not existing_tag:
                    new_tag: dict = {"value": tag, "label": tag, "children": []}
                    current_level.append(new_tag)
                    current_level = new_tag["children"]
                else:
                    current_level = existing_tag.setdefault("children", [])
        return tree

    def prune_empty_children(nodes: list[dict]):
        for node in nodes:
            children = node.get("children")
            if children:
                prune_empty_children(children)
            else:
                node.pop("children", None)
        return nodes

    return prune_empty_children(build_tree())
