"""Unit tests for FastAPI server."""

import os
import tempfile
from datetime import date
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.models import Employee
from src.server.app import app, get_repository
from src.storage.repository import EmployeeRepository


@pytest.fixture
def db_path() -> str:
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def repository(db_path: str) -> EmployeeRepository:
    """Create a repository with sample data."""
    repo = EmployeeRepository(db_path)
    employees = [
        Employee(
            id="emp-1",
            first_name="Alice",
            last_name="Johnson",
            email="alice@example.com",
            date_of_birth=date(1990, 1, 15),
            title="Ms.",
            country="USA",
            rating=4.5,
        ),
        Employee(
            id="emp-2",
            first_name="Bob",
            last_name="Smith",
            email="bob@example.com",
            date_of_birth=date(1985, 6, 20),
            title="Mr.",
            country="Canada",
            rating=3.8,
        ),
        Employee(
            id="emp-3",
            first_name="Charlie",
            last_name="Brown",
            email="charlie@example.com",
            date_of_birth=date(1992, 3, 10),
            title="Mr.",
            country="USA",
            rating=4.2,
        ),
    ]
    repo.save_employees(employees)
    return repo


@pytest.fixture
def client(repository: EmployeeRepository) -> TestClient:
    """Create a test client with mocked repository."""
    def override_get_repository() -> EmployeeRepository:
        return repository

    app.dependency_overrides[get_repository] = override_get_repository
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetEmployees:
    """Tests for GET /employees endpoint."""

    def test_get_all_employees(self, client: TestClient) -> None:
        """Test getting all employees."""
        response = client.get("/employees")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3

    def test_filter_by_country(self, client: TestClient) -> None:
        """Test filtering by country."""
        response = client.get("/employees?country=USA")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert all(e["country"] == "USA" for e in data)

    def test_filter_by_min_rating(self, client: TestClient) -> None:
        """Test filtering by minimum rating."""
        response = client.get("/employees?min_rating=4.0")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert all(e["rating"] >= 4.0 for e in data)

    def test_sort_by_first_name(self, client: TestClient) -> None:
        """Test sorting by first name."""
        response = client.get("/employees?sort=first_name")
        assert response.status_code == 200

        data = response.json()
        names = [e["first_name"] for e in data]
        assert names == ["Alice", "Bob", "Charlie"]

    def test_sort_by_rating(self, client: TestClient) -> None:
        """Test sorting by rating."""
        response = client.get("/employees?sort=rating")
        assert response.status_code == 200

        data = response.json()
        ratings = [e["rating"] for e in data]
        assert ratings == [3.8, 4.2, 4.5]

    def test_pagination(self, client: TestClient) -> None:
        """Test pagination with limit and offset."""
        response = client.get("/employees?sort=first_name&limit=2&offset=1")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["first_name"] == "Bob"

    def test_combined_filters(self, client: TestClient) -> None:
        """Test combining multiple filters."""
        response = client.get("/employees?country=USA&min_rating=4.3&sort=rating")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["first_name"] == "Alice"

    def test_csv_format(self, client: TestClient) -> None:
        """Test CSV format output."""
        response = client.get("/employees?format=csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

        content = response.text
        lines = content.strip().split("\n")
        assert len(lines) == 4
        assert "id,first_name,last_name" in lines[0]

    def test_invalid_min_rating(self, client: TestClient) -> None:
        """Test invalid min_rating value."""
        response = client.get("/employees?min_rating=invalid")
        assert response.status_code == 422

    def test_invalid_sort_field(self, client: TestClient) -> None:
        """Test invalid sort field."""
        response = client.get("/employees?sort=invalid_field")
        assert response.status_code == 422


class TestGetEmployeeById:
    """Tests for GET /employees/{id} endpoint."""

    def test_get_employee_by_id(self, client: TestClient) -> None:
        """Test getting a single employee by ID."""
        response = client.get("/employees/emp-1")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "emp-1"
        assert data["first_name"] == "Alice"

    def test_get_employee_not_found(self, client: TestClient) -> None:
        """Test 404 for non-existent employee."""
        response = client.get("/employees/non-existent")
        assert response.status_code == 404
