"""Employee API client with retry logic and error handling."""

import logging
from typing import Any

import httpx
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.auth.strategy import AuthHeaderStrategy, get_auth_strategy
from src.auth.token_client import TokenClient
from src.config import Settings
from src.models import Employee

logger = logging.getLogger(__name__)


class EmployeeClient:
    def __init__(
        self,
        settings: Settings,
        token_client: TokenClient | None = None,
        auth_strategy: AuthHeaderStrategy | None = None,
    ) -> None:
        self.settings = settings
        self.token_client = token_client or TokenClient(settings)
        self.auth_strategy = auth_strategy or get_auth_strategy(settings.auth_header_type)

    def _get_auth_headers(self) -> dict[str, str]:
        token = self.token_client.get_access_token()
        return self.auth_strategy.get_auth_header(token)

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _fetch_employees_raw(self) -> list[dict[str, Any]]:
        logger.info("Fetching employees from API")
        headers = self._get_auth_headers()

        with httpx.Client(timeout=30.0) as client:
            response = client.get(self.settings.employees_url, headers=headers)

            if response.status_code == 401:
                logger.warning("Token expired or invalid, refreshing...")
                self.token_client.clear_cache()
                headers = self._get_auth_headers()
                response = client.get(self.settings.employees_url, headers=headers)

            response.raise_for_status()
            data = response.json()

        if not isinstance(data, list):
            logger.warning(f"Expected list of employees, got {type(data)}")
            return []

        logger.info(f"Fetched {len(data)} raw employee records")
        return data

    def fetch_employees(self) -> list[Employee]:
        """Fetch and validate employees. Malformed records are skipped."""
        raw_employees = self._fetch_employees_raw()

        if not raw_employees:
            logger.warning("Empty employee list received from API")
            return []

        employees: list[Employee] = []
        for idx, raw in enumerate(raw_employees):
            try:
                employee = Employee.from_api_response(raw)
                employees.append(employee)
            except ValidationError as e:
                logger.warning(
                    f"Skipping malformed employee record at index {idx}: {e.error_count()} errors"
                )
                logger.debug(f"Validation errors: {e.errors()}")
            except Exception as e:
                logger.warning(f"Unexpected error processing record at index {idx}: {e}")

        logger.info(f"Successfully validated {len(employees)}/{len(raw_employees)} employees")
        return employees
