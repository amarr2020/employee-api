"""Mock test server that simulates the external API."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.mock_server.data import SAMPLE_EMPLOYEES

app = FastAPI(
    title="Mock Employee API",
    description="Mock server simulating the external employee API for testing",
    version="0.1.0",
)

_valid_tokens: dict[str, datetime] = {}


class TokenRequest(BaseModel):
    """Token request payload."""

    grant_type: str
    client_id: str
    client_secret: str
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response payload."""

    access_token: str
    token_type: str
    expires_at: str


@app.post("/api/token/", response_model=TokenResponse)
def create_token(request: TokenRequest) -> TokenResponse:
    """Authenticate and return an access token.

    Accepts any non-empty credentials for testing purposes.
    """
    if not all([
        request.grant_type,
        request.client_id,
        request.client_secret,
        request.username,
        request.password,
    ]):
        raise HTTPException(status_code=400, detail="All credential fields are required")

    if request.grant_type != "password":
        raise HTTPException(status_code=400, detail="Only 'password' grant_type is supported")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    _valid_tokens[token] = expires_at

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at.isoformat(),
    )


@app.get("/api/employee/list/")
def list_employees(
    access_token: str | None = Header(None, alias="Access-Token"),
) -> list[dict]:
    """Return list of employees.

    Requires valid Access-Token header.
    """
    if access_token is None:
        raise HTTPException(status_code=401, detail="Access-Token header is required")

    if access_token not in _valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    expires_at = _valid_tokens[access_token]
    if datetime.now(timezone.utc) >= expires_at:
        del _valid_tokens[access_token]
        raise HTTPException(status_code=401, detail="Token has expired")

    return SAMPLE_EMPLOYEES


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "server": "mock"}
