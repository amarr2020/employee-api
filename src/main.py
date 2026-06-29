"""CLI entry points for the employee API application."""

import argparse
import asyncio
import json
import logging
import sys

import uvicorn

from src.client.async_employee_client import AsyncEmployeeClient
from src.client.employee_client import EmployeeClient
from src.config import Settings, get_settings, setup_logging
from src.storage.repository import EmployeeRepository


def fetch_and_store(settings: Settings | None = None) -> int:
    """Fetch employees from API and store them locally."""
    setup_logging()
    logger = logging.getLogger(__name__)

    if settings is None:
        settings = get_settings()

    logger.info("Starting employee fetch")

    try:
        client = EmployeeClient(settings)
        employees = client.fetch_employees()

        if not employees:
            logger.warning("No employees fetched")
            return 0

        repository = EmployeeRepository(settings.db_path)
        count = repository.save_employees(employees)

        logger.info(f"Successfully stored {count} employees")
        return count

    except Exception as e:
        logger.error(f"Failed to fetch and store employees: {e}")
        raise


async def async_fetch_and_store(settings: Settings | None = None) -> int:
    """Fetch employees from API asynchronously and store them locally."""
    setup_logging()
    logger = logging.getLogger(__name__)

    if settings is None:
        settings = get_settings()

    logger.info("Starting employee fetch (async)")

    try:
        client = AsyncEmployeeClient(settings)
        employees = await client.fetch_employees()

        if not employees:
            logger.warning("No employees fetched")
            return 0

        repository = EmployeeRepository(settings.db_path)
        count = repository.save_employees(employees)

        logger.info(f"Successfully stored {count} employees")
        return count

    except Exception as e:
        logger.error(f"Failed to fetch and store employees: {e}")
        raise


def export_employees(output_path: str, format: str = "json") -> None:
    """Export stored employees to a file."""
    setup_logging()
    logger = logging.getLogger(__name__)

    settings = get_settings()
    repository = EmployeeRepository(settings.db_path)
    employees = repository.get_employees()

    if not employees:
        logger.warning("No employees to export")
        return

    if format == "json":
        data = [
            {
                "id": e.id,
                "first_name": e.first_name,
                "last_name": e.last_name,
                "email": e.email,
                "date_of_birth": e.date_of_birth.isoformat(),
                "title": e.title,
                "image": e.image,
                "address": e.address,
                "country": e.country,
                "bio": e.bio,
                "rating": e.rating,
                "fetched_at": e.fetched_at.isoformat(),
            }
            for e in employees
        ]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
    elif format == "csv":
        import csv

        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "first_name", "last_name", "email", "date_of_birth",
                "title", "image", "address", "country", "bio", "rating", "fetched_at"
            ])
            for e in employees:
                writer.writerow([
                    e.id, e.first_name, e.last_name, e.email,
                    e.date_of_birth.isoformat(), e.title, e.image,
                    e.address, e.country, e.bio, e.rating,
                    e.fetched_at.isoformat()
                ])

    logger.info(f"Exported {len(employees)} employees to {output_path}")


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    setup_logging()
    uvicorn.run("src.server.app:app", host=host, port=port, reload=False)


def run_mock_server(host: str = "0.0.0.0", port: int = 8001) -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting mock server on {host}:{port}")
    uvicorn.run("src.mock_server.app:app", host=host, port=port, reload=False)


def fetch_command() -> None:
    parser = argparse.ArgumentParser(description="Fetch employees from API and store locally")
    parser.add_argument(
        "--export-json",
        type=str,
        help="Export to JSON file after fetching",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        help="Export to CSV file after fetching",
    )
    args = parser.parse_args()

    try:
        count = fetch_and_store()
        print(f"Fetched and stored {count} employees")

        if args.export_json:
            export_employees(args.export_json, "json")
            print(f"Exported to {args.export_json}")

        if args.export_csv:
            export_employees(args.export_csv, "csv")
            print(f"Exported to {args.export_csv}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def serve_command() -> None:
    parser = argparse.ArgumentParser(description="Run the employee HTTP API server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)


def mock_command() -> None:
    parser = argparse.ArgumentParser(description="Run the mock test server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to listen on (default: 8001)",
    )
    args = parser.parse_args()

    run_mock_server(host=args.host, port=args.port)


def async_fetch_command() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch employees from API asynchronously and store locally"
    )
    parser.add_argument(
        "--export-json",
        type=str,
        help="Export to JSON file after fetching",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        help="Export to CSV file after fetching",
    )
    args = parser.parse_args()

    try:
        count = asyncio.run(async_fetch_and_store())
        print(f"Fetched and stored {count} employees (async)")

        if args.export_json:
            export_employees(args.export_json, "json")
            print(f"Exported to {args.export_json}")

        if args.export_csv:
            export_employees(args.export_csv, "csv")
            print(f"Exported to {args.export_csv}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Employee API CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch and store employees")
    fetch_parser.add_argument("--export-json", type=str, help="Export to JSON file")
    fetch_parser.add_argument("--export-csv", type=str, help="Export to CSV file")

    async_fetch_parser = subparsers.add_parser("async-fetch", help="Fetch employees asynchronously")
    async_fetch_parser.add_argument("--export-json", type=str, help="Export to JSON file")
    async_fetch_parser.add_argument("--export-csv", type=str, help="Export to CSV file")

    serve_parser = subparsers.add_parser("serve", help="Run HTTP server")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)

    mock_parser = subparsers.add_parser("mock", help="Run mock test server")
    mock_parser.add_argument("--host", type=str, default="0.0.0.0")
    mock_parser.add_argument("--port", type=int, default=8001)

    args = parser.parse_args()

    if args.command == "fetch":
        try:
            count = fetch_and_store()
            print(f"Fetched and stored {count} employees")
            if args.export_json:
                export_employees(args.export_json, "json")
            if args.export_csv:
                export_employees(args.export_csv, "csv")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "async-fetch":
        try:
            count = asyncio.run(async_fetch_and_store())
            print(f"Fetched and stored {count} employees (async)")
            if args.export_json:
                export_employees(args.export_json, "json")
            if args.export_csv:
                export_employees(args.export_csv, "csv")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "serve":
        run_server(host=args.host, port=args.port)
    elif args.command == "mock":
        run_mock_server(host=args.host, port=args.port)
    else:
        parser.print_help()
