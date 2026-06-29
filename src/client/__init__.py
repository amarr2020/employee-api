"""API client module."""

from src.client.async_employee_client import AsyncEmployeeClient
from src.client.employee_client import EmployeeClient

__all__ = ["EmployeeClient", "AsyncEmployeeClient"]
