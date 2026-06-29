"""Unit tests for storage repository."""

import os
import tempfile
from datetime import date, datetime

import pytest

from src.models import Employee
from src.storage.repository import EmployeeRepository


class TestEmployeeRepository:
    """Tests for EmployeeRepository."""

    @pytest.fixture
    def db_path(self) -> str:
        """Create a temporary database file."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        os.unlink(path)

    @pytest.fixture
    def repository(self, db_path: str) -> EmployeeRepository:
        """Create a repository instance."""
        return EmployeeRepository(db_path)

    @pytest.fixture
    def sample_employees(self) -> list[Employee]:
        """Create sample employees."""
        return [
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

    def test_save_and_retrieve_employees(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test saving and retrieving employees."""
        count = repository.save_employees(sample_employees)
        assert count == 3

        employees = repository.get_employees()
        assert len(employees) == 3

    def test_get_employee_by_id(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test getting a single employee by ID."""
        repository.save_employees(sample_employees)

        employee = repository.get_employee_by_id("emp-1")
        assert employee is not None
        assert employee.first_name == "Alice"

        employee = repository.get_employee_by_id("non-existent")
        assert employee is None

    def test_filter_by_country(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test filtering employees by country."""
        repository.save_employees(sample_employees)

        usa_employees = repository.get_employees(country="USA")
        assert len(usa_employees) == 2
        assert all(e.country == "USA" for e in usa_employees)

        canada_employees = repository.get_employees(country="Canada")
        assert len(canada_employees) == 1
        assert canada_employees[0].first_name == "Bob"

    def test_filter_by_min_rating(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test filtering employees by minimum rating."""
        repository.save_employees(sample_employees)

        high_rated = repository.get_employees(min_rating=4.0)
        assert len(high_rated) == 2
        assert all(e.rating >= 4.0 for e in high_rated)

    def test_combined_filters(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test combining country and rating filters."""
        repository.save_employees(sample_employees)

        result = repository.get_employees(country="USA", min_rating=4.3)
        assert len(result) == 1
        assert result[0].first_name == "Alice"

    def test_sort_by_first_name(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test sorting by first name."""
        repository.save_employees(sample_employees)

        sorted_employees = repository.get_employees(sort="first_name")
        names = [e.first_name for e in sorted_employees]
        assert names == ["Alice", "Bob", "Charlie"]

    def test_sort_by_last_name(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test sorting by last name."""
        repository.save_employees(sample_employees)

        sorted_employees = repository.get_employees(sort="last_name")
        names = [e.last_name for e in sorted_employees]
        assert names == ["Brown", "Johnson", "Smith"]

    def test_sort_by_rating(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test sorting by rating."""
        repository.save_employees(sample_employees)

        sorted_employees = repository.get_employees(sort="rating")
        ratings = [e.rating for e in sorted_employees]
        assert ratings == [3.8, 4.2, 4.5]

    def test_sort_by_date_of_birth(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test sorting by date of birth."""
        repository.save_employees(sample_employees)

        sorted_employees = repository.get_employees(sort="date_of_birth")
        dates = [e.date_of_birth for e in sorted_employees]
        assert dates == [date(1985, 6, 20), date(1990, 1, 15), date(1992, 3, 10)]

    def test_pagination_limit(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test limit parameter."""
        repository.save_employees(sample_employees)

        limited = repository.get_employees(limit=2)
        assert len(limited) == 2

    def test_pagination_offset(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test offset parameter."""
        repository.save_employees(sample_employees)

        all_employees = repository.get_employees(sort="first_name")
        offset_employees = repository.get_employees(sort="first_name", offset=1)

        assert len(offset_employees) == 2
        assert offset_employees[0].first_name == all_employees[1].first_name

    def test_pagination_limit_and_offset(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test combining limit and offset."""
        repository.save_employees(sample_employees)

        result = repository.get_employees(sort="first_name", limit=1, offset=1)
        assert len(result) == 1
        assert result[0].first_name == "Bob"

    def test_count(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test counting employees."""
        assert repository.count() == 0

        repository.save_employees(sample_employees)
        assert repository.count() == 3

    def test_clear(
        self, repository: EmployeeRepository, sample_employees: list[Employee]
    ) -> None:
        """Test clearing all employees."""
        repository.save_employees(sample_employees)
        assert repository.count() == 3

        repository.clear()
        assert repository.count() == 0

    def test_update_existing_employee(
        self, repository: EmployeeRepository
    ) -> None:
        """Test that saving an employee with same ID updates it."""
        employee1 = Employee(
            id="emp-1",
            first_name="Original",
            last_name="Name",
            email="original@example.com",
            date_of_birth=date(1990, 1, 1),
        )
        repository.save_employees([employee1])

        employee2 = Employee(
            id="emp-1",
            first_name="Updated",
            last_name="Name",
            email="updated@example.com",
            date_of_birth=date(1990, 1, 1),
        )
        repository.save_employees([employee2])

        assert repository.count() == 1
        employee = repository.get_employee_by_id("emp-1")
        assert employee is not None
        assert employee.first_name == "Updated"
        assert employee.email == "updated@example.com"

    def test_save_empty_list(self, repository: EmployeeRepository) -> None:
        """Test saving an empty list."""
        count = repository.save_employees([])
        assert count == 0
        assert repository.count() == 0

    def test_fetched_at_preserved(
        self, repository: EmployeeRepository
    ) -> None:
        """Test that fetched_at timestamp is preserved."""
        fetched_time = datetime(2024, 6, 15, 12, 0, 0)
        employee = Employee(
            id="emp-1",
            first_name="Test",
            last_name="User",
            email="test@example.com",
            date_of_birth=date(1990, 1, 1),
            fetched_at=fetched_time,
        )
        repository.save_employees([employee])

        retrieved = repository.get_employee_by_id("emp-1")
        assert retrieved is not None
        assert retrieved.fetched_at.year == 2024
        assert retrieved.fetched_at.month == 6
