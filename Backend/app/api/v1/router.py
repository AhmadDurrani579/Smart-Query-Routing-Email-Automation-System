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
    admin_dashboard,
    admin_reports,
    admin_announcements,
    announcements,
    admin_audit_logs,
    student_dashboard,
    notifications,
    staff_dashboard
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
api_router.include_router(admin_dashboard.router)
api_router.include_router(admin_reports.router)
api_router.include_router(admin_announcements.router)
api_router.include_router(announcements.router)
api_router.include_router(admin_audit_logs.router)
api_router.include_router(student_dashboard.router)
api_router.include_router(notifications.router)
api_router.include_router(staff_dashboard.router)