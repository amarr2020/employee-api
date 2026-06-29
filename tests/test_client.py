"""Unit tests for employee API client."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from pytest_httpx import HTTPXMock

from src.auth.strategy import AccessTokenStrategy
from src.auth.token_client import TokenClient
from src.client.employee_client import EmployeeClient
from src.config import Settings


class TestEmployeeClient:
    """Tests for EmployeeClient."""

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
    def mock_token_client(self) -> MagicMock:
        """Create a mock token client."""
        mock = MagicMock(spec=TokenClient)
        mock.get_access_token.return_value = "test_token"
        return mock

    @pytest.fixture
    def sample_employees(self) -> list[dict]:
        """Sample employee data from API."""
        return [
            {
                "id": "8c8c13b6-35ed-3ffb-92d5-c438825df67f",
                "date_of_birth": "1990-06-29",
                "image": "https://example.com/image.jpg",
                "email": "user1@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "title": "Mr.",
                "address": "123 Main St",
                "country": "USA",
                "bio": "Test bio",
                "rating": "4.5",
            },
            {
                "id": "9d9d24c7-46fe-4gfc-a3e6-d549936ef78g",
                "date_of_birth": "1985-03-15",
                "image": "https://example.com/image2.jpg",
                "email": "user2@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "title": "Ms.",
                "address": "456 Oak Ave",
                "country": "Canada",
                "bio": "Another bio",
                "rating": "3.8",
            },
        ]

    def test_fetch_employees_success(
        self,
        settings: Settings,
        mock_token_client: MagicMock,
        sample_employees: list[dict],
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test successful employee fetch."""
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=sample_employees,
        )

        client = EmployeeClient(
            settings,
            token_client=mock_token_client,
            auth_strategy=AccessTokenStrategy(),
        )
        employees = client.fetch_employees()

        assert len(employees) == 2
        assert employees[0].first_name == "John"
        assert employees[1].first_name == "Jane"
        assert employees[0].rating == 4.5
        assert employees[1].rating == 3.8

    def test_fetch_employees_uses_access_token_header(
        self,
        settings: Settings,
        mock_token_client: MagicMock,
        sample_employees: list[dict],
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that Access-Token header is used."""
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=sample_employees,
        )

        client = EmployeeClient(
            settings,
            token_client=mock_token_client,
            auth_strategy=AccessTokenStrategy(),
        )
        client.fetch_employees()

        request = httpx_mock.get_requests()[0]
        assert request.headers.get("Access-Token") == "test_token"

    def test_fetch_employees_handles_empty_list(
        self,
        settings: Settings,
        mock_token_client: MagicMock,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test handling of empty employee list."""
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=[],
        )

        client = EmployeeClient(
            settings,
            token_client=mock_token_client,
            auth_strategy=AccessTokenStrategy(),
        )
        employees = client.fetch_employees()

        assert employees == []

    def test_fetch_employees_skips_malformed_records(
        self,
        settings: Settings,
        mock_token_client: MagicMock,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that malformed records are skipped."""
        data = [
            {
                "id": "valid-id",
                "date_of_birth": "1990-06-29",
                "email": "valid@example.com",
                "first_name": "Valid",
                "last_name": "User",
            },
            {
                "id": "invalid-id",
                "date_of_birth": "1990-06-29",
                "email": "invalid-email",
                "first_name": "Invalid",
                "last_name": "User",
            },
            {
                "id": "missing-fields",
            },
        ]
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=data,
        )

        client = EmployeeClient(
            settings,
            token_client=mock_token_client,
            auth_strategy=AccessTokenStrategy(),
        )
        employees = client.fetch_employees()

        assert len(employees) == 1
        assert employees[0].first_name == "Valid"

    def test_fetch_employees_handles_token_expiry(
        self,
        settings: Settings,
        sample_employees: list[dict],
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that 401 triggers token refresh."""
        mock_token_client = MagicMock(spec=TokenClient)
        mock_token_client.get_access_token.side_effect = [
            "expired_token",
            "fresh_token",
        ]

        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            status_code=401,
        )
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=sample_employees,
        )

        client = EmployeeClient(
            settings,
            token_client=mock_token_client,
            auth_strategy=AccessTokenStrategy(),
        )
        employees = client.fetch_employees()

        assert len(employees) == 2
        mock_token_client.clear_cache.assert_called_once()

    def test_fetch_employees_with_unknown_fields(
        self,
        settings: Settings,
        mock_token_client: MagicMock,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that unknown fields are tolerated."""
        data = [
            {
                "id": "test-id",
                "date_of_birth": "1990-06-29",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "unknown_field": "should be ignored",
                "another_unknown": 123,
            },
        ]
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=data,
        )

        client = EmployeeClient(
            settings,
            token_client=mock_token_client,
            auth_strategy=AccessTokenStrategy(),
        )
        employees = client.fetch_employees()

        assert len(employees) == 1
        assert employees[0].first_name == "John"

    def test_fetch_employees_retry_on_error(
        self,
        settings: Settings,
        mock_token_client: MagicMock,
        sample_employees: list[dict],
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test retry on transient HTTP errors."""
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            status_code=500,
        )
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=sample_employees,
        )

        client = EmployeeClient(
            settings,
            token_client=mock_token_client,
            auth_strategy=AccessTokenStrategy(),
        )
        employees = client.fetch_employees()

        assert len(employees) == 2
        assert len(httpx_mock.get_requests()) == 2
