"""Code editor API routers."""
from fastapi import APIRouter

from .boilerplate import router as boilerplate_router
from .details import router as details_router
from .metadata import router as metadata_router
from .population_json import router as population_json_router
from .promote import router as promote_router
from .schema import router as schema_router

router = APIRouter()
router.include_router(details_router)
router.include_router(schema_router)
router.include_router(boilerplate_router)
router.include_router(metadata_router)
router.include_router(population_json_router)
router.include_router(promote_router)
