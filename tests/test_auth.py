"""Unit tests for authentication module."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pytest_httpx import HTTPXMock

from src.auth.strategy import (
    AccessTokenStrategy,
    BearerTokenStrategy,
    get_auth_strategy,
)
from src.auth.token_client import TokenClient
from src.config import Settings


class TestAuthStrategies:
    """Tests for auth header strategies."""

    def test_access_token_strategy(self) -> None:
        """Test Access-Token header strategy."""
        strategy = AccessTokenStrategy()
        assert strategy.get_header_name() == "Access-Token"
        assert strategy.format_header_value("token123") == "token123"

        header = strategy.get_auth_header("token123")
        assert header == {"Access-Token": "token123"}

    def test_bearer_token_strategy(self) -> None:
        """Test Bearer token header strategy."""
        strategy = BearerTokenStrategy()
        assert strategy.get_header_name() == "Authorization"
        assert strategy.format_header_value("token123") == "Bearer token123"

        header = strategy.get_auth_header("token123")
        assert header == {"Authorization": "Bearer token123"}

    def test_get_auth_strategy_access_token(self) -> None:
        """Test factory returns AccessTokenStrategy."""
        strategy = get_auth_strategy("access-token")
        assert isinstance(strategy, AccessTokenStrategy)

    def test_get_auth_strategy_bearer(self) -> None:
        """Test factory returns BearerTokenStrategy."""
        strategy = get_auth_strategy("bearer")
        assert isinstance(strategy, BearerTokenStrategy)

    def test_get_auth_strategy_case_insensitive(self) -> None:
        """Test factory is case insensitive."""
        strategy = get_auth_strategy("ACCESS-TOKEN")
        assert isinstance(strategy, AccessTokenStrategy)

        strategy = get_auth_strategy("BEARER")
        assert isinstance(strategy, BearerTokenStrategy)

    def test_get_auth_strategy_invalid(self) -> None:
        """Test factory raises for unknown strategy."""
        with pytest.raises(ValueError, match="Unknown auth strategy"):
            get_auth_strategy("invalid")


class TestTokenClient:
    """Tests for TokenClient."""

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

    def test_fetch_token_success(
        self, settings: Settings, token_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test successful token fetch."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )

        client = TokenClient(settings)
        token = client.get_token()

        assert token.access_token == "test_token_123"
        assert token.token_type == "bearer"

    def test_token_caching(
        self, settings: Settings, token_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test that tokens are cached and not re-fetched."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )

        client = TokenClient(settings)

        token1 = client.get_token()
        token2 = client.get_token()

        assert token1.access_token == token2.access_token
        assert len(httpx_mock.get_requests()) == 1

    def test_force_refresh(
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

        client = TokenClient(settings)

        client.get_token()
        client.get_token(force_refresh=True)

        assert len(httpx_mock.get_requests()) == 2

    def test_expired_token_refetched(
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

        client = TokenClient(settings)

        token1 = client.get_token()
        assert token1.access_token == "expired_token"

        token2 = client.get_token()
        assert token2.access_token == "fresh_token"

    def test_clear_cache(
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

        client = TokenClient(settings)

        client.get_token()
        client.clear_cache()
        client.get_token()

        assert len(httpx_mock.get_requests()) == 2

    def test_retry_on_error(
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

        client = TokenClient(settings)
        token = client.get_token()

        assert token.access_token == "test_token_123"
        assert len(httpx_mock.get_requests()) == 2
