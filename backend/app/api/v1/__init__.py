from fastapi import APIRouter 

router = APIRouter(tags=['v1'] , prefix='/v1')

from app.api.v1 import auth
router.include_router(auth.router)


