from app.core.constants import SUPER_ADMIN_ROLE
from app.system.controllers import role_controller, user_controller
from app.system.models import Menu, MenuType, Role, StatusType, User
from app.system.schemas.users import UserCreate


async def _ensure_home_menu() -> Menu:
    """Create a minimal 'home' menu for role FK requirement."""
    menu = await Menu.filter(route_name="home").first()
    if menu:
        return menu
    return await Menu.create(
        menu_name="首页",
        menu_type=MenuType.menu,
        route_name="home",
        route_path="/home",
        status_type=StatusType.enable,
        constant=False,
    )


async def seed_super_admin() -> User:
    """Create the super admin role + Soybean user. Returns the user object."""
    role = await role_controller.get_by_code(SUPER_ADMIN_ROLE)
    user = await user_controller.get_by_username("Soybean")
    if user:
        return user

    home_menu = await _ensure_home_menu()
    if not role:
        role = await Role.create(role_name="超级管理员", role_code=SUPER_ADMIN_ROLE, role_desc="超级管理员", by_role_home=home_menu)

    user = await user_controller.create(
        UserCreate(
            userName="Soybean",  # type: ignore
            userEmail="admin@admin.com",  # type: ignore
            password="123456",
            byUserRoleCodeList=[SUPER_ADMIN_ROLE],  # type: ignore
        )
    )
    await user.by_user_roles.add(role)
    return user


async def seed_roles() -> list[Role]:
    """Create R_SUPER, R_ADMIN, R_USER roles if they don't exist."""
    home_menu = await _ensure_home_menu()
    roles = []
    for name, code, desc in [
        ("超级管理员", SUPER_ADMIN_ROLE, "超级管理员"),
        ("管理员", "R_ADMIN", "管理员"),
        ("普通用户", "R_USER", "普通用户"),
    ]:
        role = await role_controller.get_by_code(code)
        if not role:
            role = await Role.create(role_name=name, role_code=code, role_desc=desc, by_role_home=home_menu)
        roles.append(role)
    return roles


async def seed_test_users(count: int = 3) -> list[User]:
    """Create test users with R_USER role."""
    role = await role_controller.get_by_code("R_USER")
    users = []
    for i in range(count):
        username = f"test_user_{i}"
        existing = await user_controller.get_by_username(username)
        if existing:
            users.append(existing)
            continue
        user = await user_controller.create(
            UserCreate(
                userName=username,  # type: ignore
                userEmail=f"test_{i}@test.com",  # type: ignore
                password="123456",
                byUserRoleCodeList=["R_USER"],  # type: ignore
            )
        )
        if role:
            await user.by_user_roles.add(role)
        users.append(user)
    return users
