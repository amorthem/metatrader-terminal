from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.utils.config import settings
from app.services.connector import mt5_connector
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    login: int
    password: str
    server: str

@router.post("/login")
def login(request: LoginRequest):
    """
    Switches MT5 to the given account credentials.
    If successful, returns the deterministic API_KEY for future requests.
    """
    mt5_connector.connect(
        login=request.login,
        password=request.password,
        server=request.server,
    )

    logger.info(f"MT5 account switched to {request.login} on {request.server}")
    return {
        "message": "Login successful",
        "api_key": settings.api_key,
        "login": request.login,
        "server": request.server
    }
