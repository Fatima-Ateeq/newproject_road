from fastapi import APIRouter

from app.api.routes import admin_complaints, auth, complaints

api_router = APIRouter(prefix="/api")
api_router.include_router(complaints.router)
api_router.include_router(auth.router)
api_router.include_router(admin_complaints.router)


@api_router.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok"}
