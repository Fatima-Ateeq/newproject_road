from fastapi import APIRouter

from app.api.deps import AuthServiceDep
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/admin", tags=["Administrator"])


@router.post("/login")
def login(credentials: LoginRequest, auth: AuthServiceDep) -> TokenResponse:
    return TokenResponse(access_token=auth.login(credentials.username, credentials.password))
