"""Unit tests for Pydantic models."""

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import Employee, EmployeeBase, Token


class TestToken:
    """Tests for Token model."""

    def test_token_creation(self) -> None:
        """Test basic token creation."""
        token = Token(
            access_token="abc123",
            token_type="bearer",
            expires_at=datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"

    def test_token_expires_at_parsing(self) -> None:
        """Test parsing expires_at from ISO string."""
        token = Token(
            access_token="abc123",
            token_type="bearer",
            expires_at="2025-12-31T23:59:59+00:00",
        )
        assert token.expires_at.year == 2025
        assert token.expires_at.month == 12

    def test_token_is_expired(self) -> None:
        """Test token expiry check."""
        expired_token = Token(
            access_token="abc123",
            token_type="bearer",
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        assert expired_token.is_expired()

        future_token = Token(
            access_token="abc123",
            token_type="bearer",
            expires_at=datetime(2099, 12, 31, tzinfo=timezone.utc),
        )
        assert not future_token.is_expired()


class TestEmployeeBase:
    """Tests for EmployeeBase model."""

    def test_employee_creation(self) -> None:
        """Test basic employee creation."""
        employee = EmployeeBase(
            id="123",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth="1990-01-15",
        )
        assert employee.id == "123"
        assert employee.first_name == "John"
        assert employee.email == "john@example.com"
        assert employee.date_of_birth == date(1990, 1, 15)

    def test_email_validation(self) -> None:
        """Test that invalid emails are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmployeeBase(
                id="123",
                first_name="John",
                last_name="Doe",
                email="invalid-email",
                date_of_birth="1990-01-15",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("email",) for e in errors)

    def test_date_of_birth_validation(self) -> None:
        """Test that invalid dates are rejected."""
        with pytest.raises(ValidationError):
            EmployeeBase(
                id="123",
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                date_of_birth="not-a-date",
            )

    def test_rating_normalization_from_string(self) -> None:
        """Test rating is converted from string to float."""
        employee = EmployeeBase(
            id="123",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth="1990-01-15",
            rating="3.0600000000000001",
        )
        assert employee.rating == 3.0600000000000001
        assert isinstance(employee.rating, float)

    def test_rating_normalization_from_int(self) -> None:
        """Test rating is converted from int to float."""
        employee = EmployeeBase(
            id="123",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth="1990-01-15",
            rating=4,
        )
        assert employee.rating == 4.0
        assert isinstance(employee.rating, float)

    def test_rating_invalid_defaults_to_zero(self) -> None:
        """Test invalid rating defaults to 0.0."""
        employee = EmployeeBase(
            id="123",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth="1990-01-15",
            rating="not-a-number",
        )
        assert employee.rating == 0.0

    def test_unknown_fields_are_ignored(self) -> None:
        """Test that unknown fields are tolerated and ignored."""
        employee = EmployeeBase(
            id="123",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth="1990-01-15",
            unknown_field="should be ignored",
            another_unknown=123,
        )
        assert employee.id == "123"
        assert not hasattr(employee, "unknown_field")

    def test_optional_fields_have_defaults(self) -> None:
        """Test optional fields have sensible defaults."""
        employee = EmployeeBase(
            id="123",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth="1990-01-15",
        )
        assert employee.title == ""
        assert employee.image == ""
        assert employee.address == ""
        assert employee.country == ""
        assert employee.bio == ""
        assert employee.rating == 0.0

    def test_whitespace_stripped(self) -> None:
        """Test that string fields have whitespace stripped."""
        employee = EmployeeBase(
            id="  123  ",
            first_name="  John  ",
            last_name="  Doe  ",
            email="john@example.com",
            date_of_birth="1990-01-15",
        )
        assert employee.id == "123"
        assert employee.first_name == "John"
        assert employee.last_name == "Doe"


class TestEmployee:
    """Tests for Employee model with fetched_at."""

    def test_employee_has_fetched_at(self) -> None:
        """Test Employee includes fetched_at timestamp."""
        employee = Employee(
            id="123",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth="1990-01-15",
        )
        assert employee.fetched_at is not None
        assert isinstance(employee.fetched_at, datetime)

    def test_from_api_response(self) -> None:
        """Test creating Employee from API response dict."""
        data = {
            "id": "8c8c13b6-35ed-3ffb-92d5-c438825df67f",
            "date_of_birth": "1990-06-29",
            "image": "https://example.com/image.jpg",
            "email": "user@example.com",
            "first_name": "Dayni",
            "last_name": "Mayez",
            "title": "Mr.",
            "address": "18342 Alisa Square Suite 259",
            "country": "USA",
            "bio": "Some bio text",
            "rating": "3.0600000000000001",
        }
        employee = Employee.from_api_response(data)

        assert employee.id == "8c8c13b6-35ed-3ffb-92d5-c438825df67f"
        assert employee.first_name == "Dayni"
        assert employee.rating == 3.0600000000000001
        assert employee.date_of_birth == date(1990, 6, 29)


class TestValidationEdgeCases:
    """Tests for validation edge cases."""

    def test_required_fields_missing(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EmployeeBase(
                id="123",
                first_name="John",
            )
        errors = exc_info.value.errors()
        assert len(errors) >= 2

    def test_empty_id_allowed(self) -> None:
        """Test that empty string ID is allowed (validation is not strict)."""
        employee = EmployeeBase(
            id="",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            date_of_birth="1990-01-15",
        )
        assert employee.id == ""
