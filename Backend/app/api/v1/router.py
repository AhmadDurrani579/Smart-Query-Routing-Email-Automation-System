from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    queries,
    departments,
    admin,
    admin_queries,
    internal,
    ai,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(queries.router)
api_router.include_router(departments.router)
api_router.include_router(admin.router)
api_router.include_router(admin_queries.router)
api_router.include_router(internal.router)
api_router.include_router(ai.router)