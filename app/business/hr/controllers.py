"""
HR controllers — 基于 CRUDBase 的控制器。
"""

from app.business.hr.models import Department, Employee, Skill
from app.utils import CRUDBase

department_controller = CRUDBase(model=Department)
tag_controller = CRUDBase(model=Skill)
employee_controller = CRUDBase(model=Employee)
