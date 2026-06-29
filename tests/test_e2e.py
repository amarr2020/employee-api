"""End-to-end happy path test: fetch -> store -> GET /employees."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

from src.auth.token_client import TokenClient
from src.client.employee_client import EmployeeClient
from src.config import Settings
from src.server.app import app, get_repository
from src.storage.repository import EmployeeRepository


class TestE2EHappyPath:
    """End-to-end test for the complete fetch -> store -> serve flow."""

    @pytest.fixture
    def db_path(self) -> str:
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def settings(self, db_path: str) -> Settings:
        """Create test settings."""
        return Settings(
            api_base_url="http://test-api.local",
            api_client_id="test_client",
            api_client_secret="test_secret",
            api_username="test_user",
            api_password="test_pass",
            database_url=f"sqlite:///{db_path}",
        )

    @pytest.fixture
    def token_response(self) -> dict:
        """Create a valid token response."""
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        return {
            "access_token": "e2e_test_token",
            "token_type": "bearer",
            "expires_at": expires.isoformat(),
        }

    @pytest.fixture
    def employees_response(self) -> list[dict]:
        """Sample employee data from API."""
        return [
            {
                "id": "8c8c13b6-35ed-3ffb-92d5-c438825df67f",
                "date_of_birth": "1990-06-29",
                "image": "https://lorempixel.com/640/480/people/?96612",
                "email": "andres34@gmail.com",
                "first_name": "Dayni",
                "last_name": "Mayez",
                "title": "Mr.",
                "address": "18342 Alisa Square Suite 259",
                "country": "USA",
                "bio": "Software engineer with 10 years experience.",
                "rating": "3.0600000000000001",
            },
            {
                "id": "9d9d24c7-46fe-4gfc-a3e6-d549936ef78g",
                "date_of_birth": "1985-03-15",
                "image": "https://lorempixel.com/640/480/people/?12345",
                "email": "jane.smith@example.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "title": "Ms.",
                "address": "456 Oak Avenue",
                "country": "Canada",
                "bio": "Product manager passionate about user experience.",
                "rating": "4.5",
            },
            {
                "id": "abc12345-def6-7890-ghij-klmnopqrstuv",
                "date_of_birth": "1992-11-22",
                "image": "https://lorempixel.com/640/480/people/?67890",
                "email": "bob.wilson@company.org",
                "first_name": "Bob",
                "last_name": "Wilson",
                "title": "Dr.",
                "address": "789 Pine Street",
                "country": "USA",
                "bio": "Data scientist specializing in machine learning.",
                "rating": "4.2",
            },
        ]

    def test_full_flow_fetch_store_serve(
        self,
        settings: Settings,
        db_path: str,
        token_response: dict,
        employees_response: list[dict],
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test the complete happy path: fetch employees, store, then serve via API."""
        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=employees_response,
        )

        token_client = TokenClient(settings)
        employee_client = EmployeeClient(settings, token_client=token_client)
        employees = employee_client.fetch_employees()

        assert len(employees) == 3
        assert employees[0].first_name == "Dayni"
        assert employees[0].rating == 3.0600000000000001

        repository = EmployeeRepository(db_path)
        count = repository.save_employees(employees)

        assert count == 3
        assert repository.count() == 3

        def override_get_repository() -> EmployeeRepository:
            return repository

        app.dependency_overrides[get_repository] = override_get_repository
        client = TestClient(app)

        response = client.get("/employees")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        response = client.get("/employees?country=USA")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(e["country"] == "USA" for e in data)

        response = client.get("/employees?min_rating=4.0")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(e["rating"] >= 4.0 for e in data)

        response = client.get("/employees?sort=first_name")
        assert response.status_code == 200
        data = response.json()
        names = [e["first_name"] for e in data]
        assert names == ["Bob", "Dayni", "Jane"]

        response = client.get("/employees/8c8c13b6-35ed-3ffb-92d5-c438825df67f")
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Dayni"
        assert data["email"] == "andres34@gmail.com"

        response = client.get("/employees?format=csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        lines = response.text.strip().split("\n")
        assert len(lines) == 4

        app.dependency_overrides.clear()

    def test_flow_with_malformed_records(
        self,
        settings: Settings,
        db_path: str,
        token_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that malformed records are skipped but valid ones are processed."""
        employees_with_errors = [
            {
                "id": "valid-1",
                "date_of_birth": "1990-06-29",
                "email": "valid@example.com",
                "first_name": "Valid",
                "last_name": "User",
                "country": "USA",
                "rating": "4.0",
            },
            {
                "id": "invalid-email",
                "date_of_birth": "1990-06-29",
                "email": "not-an-email",
                "first_name": "Invalid",
                "last_name": "Email",
            },
            {
                "id": "missing-fields",
            },
            {
                "id": "valid-2",
                "date_of_birth": "1985-03-15",
                "email": "another@example.com",
                "first_name": "Another",
                "last_name": "Valid",
                "country": "Canada",
                "rating": "3.5",
            },
        ]

        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=employees_with_errors,
        )

        token_client = TokenClient(settings)
        employee_client = EmployeeClient(settings, token_client=token_client)
        employees = employee_client.fetch_employees()

        assert len(employees) == 2

        repository = EmployeeRepository(db_path)
        repository.save_employees(employees)

        def override_get_repository() -> EmployeeRepository:
            return repository

        app.dependency_overrides[get_repository] = override_get_repository
        client = TestClient(app)

        response = client.get("/employees")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert {e["first_name"] for e in data} == {"Valid", "Another"}

        app.dependency_overrides.clear()

    def test_flow_with_unknown_fields(
        self,
        settings: Settings,
        db_path: str,
        token_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that unknown fields in API response are tolerated."""
        employees_with_unknown = [
            {
                "id": "emp-1",
                "date_of_birth": "1990-06-29",
                "email": "user@example.com",
                "first_name": "Test",
                "last_name": "User",
                "country": "USA",
                "rating": "4.0",
                "unknown_field": "should be ignored",
                "another_unknown": 12345,
                "nested_unknown": {"key": "value"},
            },
        ]

        httpx_mock.add_response(
            url="http://test-api.local/api/token/",
            method="POST",
            json=token_response,
        )
        httpx_mock.add_response(
            url="http://test-api.local/api/employee/list/",
            method="GET",
            json=employees_with_unknown,
        )

        token_client = TokenClient(settings)
        employee_client = EmployeeClient(settings, token_client=token_client)
        employees = employee_client.fetch_employees()

        assert len(employees) == 1
        assert employees[0].first_name == "Test"

        repository = EmployeeRepository(db_path)
        repository.save_employees(employees)

        def override_get_repository() -> EmployeeRepository:
            return repository

        app.dependency_overrides[get_repository] = override_get_repository
        client = TestClient(app)

        response = client.get("/employees")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "unknown_field" not in data[0]

        app.dependency_overrides.clear()
