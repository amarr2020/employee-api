"""Unit tests for async authentication module."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pytest_httpx import HTTPXMock

from src.auth.async_token_client import AsyncTokenClient
from src.config import Settings


class TestAsyncTokenClient:
    """Tests for AsyncTokenClient."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create test settings."""
        return Settings(
            api_base_url="http://test-api.local",
            api_client_id="test_client",
            api_client_secret="test_secret",
            api_username="test_user",
            api_password="test_pass",
            database_url="sqlite:///./test.db",
        )

    @pytest.fixture
    def token_response(self) -> dict:
        """Create a valid token response."""
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        return {
            "access_token": "test_token_123",
            "token_type": "bearer",
            "expires_at": expires.isoformat(),
        }

    @pytest.mark.asyncio
    async def test_fetch_token_success(
        self, settings: Settings, token_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test successful token fetch."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )

        client = AsyncTokenClient(settings)
        token = await client.get_token()

        assert token.access_token == "test_token_123"
        assert token.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_token_caching(
        self, settings: Settings, token_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test that tokens are cached and not re-fetched."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )

        client = AsyncTokenClient(settings)

        token1 = await client.get_token()
        token2 = await client.get_token()

        assert token1.access_token == token2.access_token
        assert len(httpx_mock.get_requests()) == 1

    @pytest.mark.asyncio
    async def test_force_refresh(
        self, settings: Settings, token_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test force refresh bypasses cache."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )

        client = AsyncTokenClient(settings)

        await client.get_token()
        await client.get_token(force_refresh=True)

        assert len(httpx_mock.get_requests()) == 2

    @pytest.mark.asyncio
    async def test_expired_token_refetched(
        self, settings: Settings, httpx_mock: HTTPXMock
    ) -> None:
        """Test that expired tokens trigger re-fetch."""
        expired = datetime.now(timezone.utc) - timedelta(hours=1)
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json={
                "access_token": "expired_token",
                "token_type": "bearer",
                "expires_at": expired.isoformat(),
            },
        )
        valid = datetime.now(timezone.utc) + timedelta(hours=1)
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json={
                "access_token": "fresh_token",
                "token_type": "bearer",
                "expires_at": valid.isoformat(),
            },
        )

        client = AsyncTokenClient(settings)

        token1 = await client.get_token()
        assert token1.access_token == "expired_token"

        token2 = await client.get_token()
        assert token2.access_token == "fresh_token"

    @pytest.mark.asyncio
    async def test_clear_cache(
        self, settings: Settings, token_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test clearing the token cache."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )

        client = AsyncTokenClient(settings)

        await client.get_token()
        client.clear_cache()
        await client.get_token()

        assert len(httpx_mock.get_requests()) == 2

    @pytest.mark.asyncio
    async def test_get_access_token(
        self, settings: Settings, token_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test get_access_token returns just the token string."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )

        client = AsyncTokenClient(settings)
        access_token = await client.get_access_token()

        assert access_token == "test_token_123"
        assert isinstance(access_token, str)

    @pytest.mark.asyncio
    async def test_retry_on_error(
        self, settings: Settings, token_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test that transient errors trigger retry."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            status_code=500,
        )
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )

        client = AsyncTokenClient(settings)
        token = await client.get_token()

        assert token.access_token == "test_token_123"
        assert len(httpx_mock.get_requests()) == 2
