"""Token client for authentication with caching and expiry handling."""

import logging
from datetime import datetime, timedelta

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import Settings
from src.models import Token

logger = logging.getLogger(__name__)


class TokenClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cached_token: Token | None = None
        self._expiry_buffer = timedelta(seconds=30)

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _fetch_token(self) -> Token:
        logger.info("Fetching new authentication token")

        payload = {
            "grant_type": "password",
            "client_id": self.settings.api_client_id,
            "client_secret": self.settings.api_client_secret,
            "username": self.settings.api_username,
            "password": self.settings.api_password,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.settings.token_url, json=payload)
            response.raise_for_status()
            data = response.json()

        token = Token(**data)
        logger.info(f"Token obtained, expires at {token.expires_at}")
        return token

    def _is_token_valid(self) -> bool:
        if self._cached_token is None:
            return False

        now = datetime.now(self._cached_token.expires_at.tzinfo)
        return now + self._expiry_buffer < self._cached_token.expires_at

    def get_token(self, force_refresh: bool = False) -> Token:
        if force_refresh or not self._is_token_valid():
            self._cached_token = self._fetch_token()

        return self._cached_token

    def get_access_token(self, force_refresh: bool = False) -> str:
        return self.get_token(force_refresh).access_token

    def clear_cache(self) -> None:
        self._cached_token = None
        logger.debug("Token cache cleared")
