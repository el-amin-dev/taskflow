from fastapi import APIRouter 

router = APIRouter(tags=['v1'] , prefix='/v1')

from app.api.v1 import auth
from app.api.v1 import workspaces

from app.api.v1 import comments
from app.api.v1 import tasks


router.include_router(comments.router)
router.include_router(tasks.router)
router.include_router(auth.router)
router.include_router(workspaces.router)

