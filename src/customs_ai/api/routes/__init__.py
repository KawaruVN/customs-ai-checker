from fastapi import APIRouter

from . import documents, health

router = APIRouter()
router.include_router(health.router)
router.include_router(documents.router)
