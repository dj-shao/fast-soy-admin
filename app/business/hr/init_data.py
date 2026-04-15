"""
HR 模块初始化数据 — 菜单、角色、标签与演示员工。

启动时由 autodiscover 自动发现并执行 init()。
所有操作幂等，重复启动不会重复创建。
"""

from __future__ import annotations

from app.business.hr.config import BIZ_SETTINGS
from app.business.hr.models import Department, Employee, Tag
from app.system.services import ensure_menu, ensure_role, ensure_user, reconcile_menu_subtree
from app.system.services.init_helper import _safe_update_or_create

HR_MENU_CHILDREN = [
    {
        "menu_name": "部门管理",
        "route_name": "hr_department",
        "route_path": "/hr/department",
        "component": "view.hr_department",
        "icon": "mdi:office-building",
        "order": 1,
    },
    {
        "menu_name": "员工管理",
        "route_name": "hr_employee",
        "route_path": "/hr/employee",
        "component": "view.hr_employee",
        "icon": "mdi:account",
        "order": 2,
        "buttons": [
            {"button_code": "B_HR_CREATE", "button_desc": "创建员工"},
            {"button_code": "B_HR_EDIT", "button_desc": "编辑员工"},
            {"button_code": "B_HR_DELETE", "button_desc": "删除员工"},
        ],
    },
    {
        "menu_name": "标签管理",
        "route_name": "hr_tag",
        "route_path": "/hr/tag",
        "component": "view.hr_tag",
        "icon": "mdi:tag-multiple",
        "order": 3,
    },
]

HR_ROLE_SEEDS = [
    {
        "role_name": "部门主管",
        "role_code": "R_DEPT_MGR",
        "role_desc": "部门主管，可管理本部门员工",
        "menus": ["home", "hr", "hr_department", "hr_employee", "hr_tag"],
        "buttons": ["B_HR_CREATE", "B_HR_EDIT"],
        "apis": [
            ("post", "/api/v1/business/hr/employees"),
            ("post", "/api/v1/business/hr/employees/search"),
            ("patch", "/api/v1/business/hr/employees/{emp_id}"),
            ("get", "/api/v1/business/hr/employees/{item_id}"),
            ("get", "/api/v1/business/hr/department/employees"),
            ("post", "/api/v1/business/hr/departments/search"),
            ("patch", "/api/v1/business/hr/department/employees/{emp_id}/tags"),
            ("get", "/api/v1/business/hr/departments/stats"),
            ("post", "/api/v1/business/hr/tags/search"),
        ],
    }
]

HR_TAG_SEEDS = [
    {"name": "远程协作", "category": "working_style", "description": "适应远程与混合办公节奏"},
    {"name": "文档驱动", "category": "collaboration", "description": "习惯通过文档沉淀流程与信息"},
    {"name": "会议纪要", "category": "collaboration", "description": "擅长整理会议纪要与行动项"},
    {"name": "跨部门协作", "category": "collaboration", "description": "能高效连接上下游团队推进事项"},
    {"name": "新人导师", "category": "team_role", "description": "愿意承担新人带教与融入支持"},
    {"name": "活动组织", "category": "team_role", "description": "擅长组织团队活动和内部沟通"},
    {"name": "客户沟通", "category": "business", "description": "适合承担客户跟进与需求沟通"},
    {"name": "流程优化", "category": "growth", "description": "关注流程梳理与效率提升"},
]

HR_DEPARTMENT_SEEDS = [
    {"name": "技术部", "code": "TECH", "description": "负责平台研发与技术支持", "manager_employee_no": 9001},
    {"name": "市场部", "code": "MKT", "description": "负责市场活动与品牌传播", "manager_employee_no": 9003},
    {"name": "行政部", "code": "OPS", "description": "负责行政支持与办公协同", "manager_employee_no": None},
]

HR_EMPLOYEE_SEEDS = [
    {
        "user": {
            "user_name": "zhouhang",
            "password": "123456",
            "role_codes": ["R_DEPT_MGR"],
            "user_email": "zhouhang@example.com",
            "nick_name": "周航",
        },
        "employee": {
            "employee_no_serial": 9001,
            "name": "周航",
            "email": "zhouhang@example.com",
            "phone": "13800000001",
            "position": "技术主管",
            "department_code": "TECH",
            "tag_names": ["远程协作", "文档驱动", "新人导师"],
        },
    },
    {
        "user": {
            "user_name": "limu",
            "password": "123456",
            "role_codes": ["R_USER"],
            "user_email": "limu@example.com",
            "nick_name": "李沐",
        },
        "employee": {
            "employee_no_serial": 9002,
            "name": "李沐",
            "email": "limu@example.com",
            "phone": "13800000002",
            "position": "前端工程师",
            "department_code": "TECH",
            "tag_names": ["会议纪要", "跨部门协作", "流程优化"],
        },
    },
    {
        "user": {
            "user_name": "linyan",
            "password": "123456",
            "role_codes": ["R_DEPT_MGR"],
            "user_email": "linyan@example.com",
            "nick_name": "林妍",
        },
        "employee": {
            "employee_no_serial": 9003,
            "name": "林妍",
            "email": "linyan@example.com",
            "phone": "13800000003",
            "position": "市场主管",
            "department_code": "MKT",
            "tag_names": ["跨部门协作", "活动组织", "流程优化"],
        },
    },
    {
        "user": {
            "user_name": "chenxi",
            "password": "123456",
            "role_codes": ["R_USER"],
            "user_email": "chenxi@example.com",
            "nick_name": "陈希",
        },
        "employee": {
            "employee_no_serial": 9004,
            "name": "陈希",
            "email": "chenxi@example.com",
            "phone": "13800000004",
            "position": "市场专员",
            "department_code": "MKT",
            "tag_names": ["会议纪要", "活动组织", "客户沟通"],
        },
    },
    {
        "user": {
            "user_name": "songyu",
            "password": "123456",
            "role_codes": ["R_USER"],
            "user_email": "songyu@example.com",
            "nick_name": "宋羽",
        },
        "employee": {
            "employee_no_serial": 9005,
            "name": "宋羽",
            "email": "songyu@example.com",
            "phone": "13800000005",
            "position": "行政专员",
            "department_code": "OPS",
            "tag_names": ["远程协作", "文档驱动", "会议纪要"],
        },
    },
]


def _employee_no(serial: int) -> str:
    return f"{BIZ_SETTINGS.EMPLOYEE_NO_PREFIX}{serial:04d}"


def _collect_declared_routes(children: list[dict]) -> set[str]:
    """递归收集 HR_MENU_CHILDREN 中所有层级的 route_name。"""
    result: set[str] = set()
    for item in children:
        result.add(item["route_name"])
        if item.get("children"):
            result.update(_collect_declared_routes(item["children"]))
    return result


def _collect_declared_buttons(children: list[dict]) -> set[str]:
    """递归收集 HR_MENU_CHILDREN 中所有层级的 button_code。"""
    result: set[str] = set()
    for item in children:
        for btn in item.get("buttons") or []:
            result.add(btn["button_code"])
        if item.get("children"):
            result.update(_collect_declared_buttons(item["children"]))
    return result


async def _init_menu_data() -> None:
    await ensure_menu(
        menu_name="HR管理",
        route_name="hr",
        route_path="/hr",
        icon="mdi:account-group",
        order=8,
        children=HR_MENU_CHILDREN,
    )
    # HR 子树以 init_data 为唯一数据源，启动时清理不再声明的菜单/按钮。
    await reconcile_menu_subtree(
        root_route="hr",
        declared_route_names=_collect_declared_routes(HR_MENU_CHILDREN),
        declared_button_codes=_collect_declared_buttons(HR_MENU_CHILDREN),
    )


async def _init_role_data() -> None:
    for role_seed in HR_ROLE_SEEDS:
        await ensure_role(**role_seed)


async def _init_departments() -> None:
    for department_seed in HR_DEPARTMENT_SEEDS:
        defaults = {
            "name": department_seed["name"],
            "description": department_seed["description"],
        }
        await _safe_update_or_create(Department, {"code": department_seed["code"]}, defaults)


async def _init_tags() -> None:
    for tag_seed in HR_TAG_SEEDS:
        await _safe_update_or_create(
            Tag,
            {"name": tag_seed["name"]},
            {
                "category": tag_seed["category"],
                "description": tag_seed["description"],
            },
        )


async def _ensure_demo_employee(seed: dict) -> Employee:
    user = await ensure_user(**seed["user"])

    employee_seed = seed["employee"]
    department = await Department.get(code=employee_seed["department_code"])
    employee_no = _employee_no(employee_seed["employee_no_serial"])

    employee, _ = await _safe_update_or_create(
        Employee,
        {"employee_no": employee_no},
        {
            "name": employee_seed["name"],
            "email": employee_seed["email"],
            "phone": employee_seed["phone"],
            "position": employee_seed["position"],
            "user_id": user.id,
            "department_id": department.id,
        },
    )

    await employee.tags.clear()
    for tag_name in employee_seed["tag_names"]:
        tag = await Tag.get(name=tag_name)
        await employee.tags.add(tag)

    return employee


async def _init_demo_employees() -> None:
    employee_map: dict[int, Employee] = {}
    for seed in HR_EMPLOYEE_SEEDS:
        employee = await _ensure_demo_employee(seed)
        employee_map[seed["employee"]["employee_no_serial"]] = employee

    for department_seed in HR_DEPARTMENT_SEEDS:
        manager_serial = department_seed["manager_employee_no"]
        manager = employee_map.get(manager_serial) if manager_serial else None
        await Department.filter(code=department_seed["code"]).update(manager_id=manager.id if manager else None)


async def init():
    await _init_menu_data()
    await _init_role_data()
    await _init_departments()
    await _init_tags()
    await _init_demo_employees()
