from datetime import datetime

from tortoise.transactions import in_transaction

from app.core.code import Code
from app.core.crud import CRUDBase, get_db_conn
from app.core.exceptions import BizError
from app.system.models import Role, StatusType, User
from app.system.radar.developer import radar_log
from app.system.schemas.login import CredentialsSchema
from app.system.schemas.users import UserCreate, UserUpdate
from app.system.security import get_password_hash, verify_password


class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)

    async def get_by_email(self, user_email: str) -> User | None:
        return await self.model.filter(user_email=user_email).first()

    async def get_by_username(self, user_name: str) -> User | None:
        return await self.model.filter(user_name=user_name).first()

    async def create(self, obj_in: UserCreate) -> User:  # type: ignore
        obj_in.password = get_password_hash(password=obj_in.password or "")

        if not obj_in.nick_name:
            obj_in.nick_name = obj_in.user_name

        obj = await super().create(obj_in, exclude={"byUserRoles"})
        return obj

    async def update(self, user_id: int, obj_in: UserUpdate) -> User:  # type: ignore
        if obj_in.password:
            obj_in.password = get_password_hash(password=obj_in.password)
        else:
            obj_in.password = None  # type: ignore[assignment]

        return await super().update(id=user_id, obj_in=obj_in, exclude={"byUserRoles"})

    async def update_last_login(self, user_id: int) -> None:
        user = await self.model.get(id=user_id)
        user.last_login = datetime.now()
        await user.save()

    async def authenticate(self, credentials: CredentialsSchema) -> User:
        user = await self.model.filter(user_name=credentials.user_name).first()

        if not user:
            radar_log("用户登录失败: 用户名不存在", level="WARNING", data={"userName": credentials.user_name})
            raise BizError(code=Code.WRONG_CREDENTIALS, msg="用户名或密码错误")

        verified = verify_password(credentials.password or "", user.password or "")

        if not verified:
            radar_log("用户登录失败: 密码错误", level="WARNING", data={"userName": user.user_name, "userId": user.id})
            raise BizError(code=Code.WRONG_CREDENTIALS, msg="用户名或密码错误")

        if user.status_type == StatusType.disable:
            radar_log("用户登录失败: 账号已禁用", level="ERROR", data={"userName": user.user_name, "userId": user.id})
            raise BizError(code=Code.ACCOUNT_DISABLED, msg="该用户已被禁用")

        return user

    @staticmethod
    async def update_roles(user: User, role_id_list: list[int] | str) -> bool:
        if not role_id_list:
            return False

        if isinstance(role_id_list, str):
            role_id_list = [int(x) for x in role_id_list.split("|")]

        async with in_transaction(get_db_conn(User)):
            await user.by_user_roles.clear()
            user_role_objs = await Role.filter(id__in=role_id_list)
            for user_role_obj in user_role_objs:
                await user.by_user_roles.add(user_role_obj)

        return True

    @staticmethod
    async def update_roles_by_code(user: User, roles_code_list: list[str] | str) -> bool:
        if not roles_code_list:
            return False

        if isinstance(roles_code_list, str):
            roles_code_list = roles_code_list.split("|")

        async with in_transaction(get_db_conn(User)):
            user_role_objs = await Role.filter(role_code__in=roles_code_list)
            await user.by_user_roles.clear()
            for user_role_obj in user_role_objs:
                await user.by_user_roles.add(user_role_obj)

        return True


user_controller = UserController()
