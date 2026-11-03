
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://campusiq-frontend.vercel.app",
        "https://smart-query-email-automantion.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix="/api/v1"
)

@app.get("/")
def root():
    return {
        "message": "Smart Query Routing API is running",
        "status": "success"
    }

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy"}
