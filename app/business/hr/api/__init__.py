from fastapi import APIRouter

from app.business.hr.api.manage import router as manage_router
from app.business.hr.api.my import router as my_router
from app.business.hr.api.public import router as public_router
from app.business.hr.api.team import router as team_router

router = APIRouter()
router.include_router(manage_router)
router.include_router(my_router)
router.include_router(team_router)
router.include_router(public_router)
