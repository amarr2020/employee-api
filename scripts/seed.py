#!/usr/bin/env python3
"""Seed script to populate database with sample data from mock server.

This script:
1. Starts the mock server in a subprocess
2. Fetches employees from it
3. Stores them in the database
4. Exports to samples/employees.json and samples/employees.csv
5. Stops the mock server

Usage:
    python scripts/seed.py
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.client.async_employee_client import AsyncEmployeeClient
from src.config import Settings, setup_logging
from src.main import export_employees
from src.storage.repository import EmployeeRepository


def wait_for_server(url: str, timeout: int = 10) -> bool:
    """Wait for server to be ready."""
    import httpx

    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(f"{url}/health", timeout=2.0)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


async def fetch_and_store(settings: Settings) -> int:
    """Fetch employees using async client and store them."""
    client = AsyncEmployeeClient(settings)
    employees = await client.fetch_employees()

    if not employees:
        return 0

    repository = EmployeeRepository(settings.db_path)
    return repository.save_employees(employees)


def main() -> int:
    """Run the seed script."""
    setup_logging()

    print("=" * 50)
    print("Employee API - Seed Script")
    print("=" * 50)

    # Configuration
    mock_port = 8001
    mock_url = f"http://localhost:{mock_port}"

    # Create settings pointing to mock server
    settings = Settings(
        api_base_url=mock_url,
        api_client_id="seed_client",
        api_client_secret="seed_secret",
        api_username="seed_user",
        api_password="seed_pass",
        database_url="sqlite:///./employees.db",
    )

    # Ensure samples directory exists
    samples_dir = project_root / "samples"
    samples_dir.mkdir(exist_ok=True)

    # Start mock server
    print(f"\n[1/5] Starting mock server on port {mock_port}...")
    mock_process = subprocess.Popen(
        [sys.executable, "-m", "src.main", "mock", "--port", str(mock_port)],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for server to be ready
        if not wait_for_server(mock_url):
            print("ERROR: Mock server failed to start")
            mock_process.terminate()
            return 1
        print("       Mock server is ready")

        # Fetch employees
        print("\n[2/5] Fetching employees from mock server...")
        count = asyncio.run(fetch_and_store(settings))
        print(f"       Fetched and stored {count} employees")

        if count == 0:
            print("WARNING: No employees fetched")
            return 1

        # Export to JSON
        print("\n[3/5] Exporting to samples/employees.json...")
        json_path = str(samples_dir / "employees.json")
        export_employees(json_path, "json")
        print(f"       Exported to {json_path}")

        # Export to CSV
        print("\n[4/5] Exporting to samples/employees.csv...")
        csv_path = str(samples_dir / "employees.csv")
        export_employees(csv_path, "csv")
        print(f"       Exported to {csv_path}")

        print("\n[5/5] Stopping mock server...")

    finally:
        # Stop mock server
        mock_process.terminate()
        try:
            mock_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            mock_process.kill()
        print("       Mock server stopped")

    print("\n" + "=" * 50)
    print("Seed completed successfully!")
    print("=" * 50)
    print(f"\nDatabase: employees.db ({count} employees)")
    print(f"Exports:  samples/employees.json")
    print(f"          samples/employees.csv")

    return 0


if __name__ == "__main__":
    sys.exit(main())
