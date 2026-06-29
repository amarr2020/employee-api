"""SQLite storage repository for employee data."""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Generator, Literal

from src.models import Employee

logger = logging.getLogger(__name__)

SortField = Literal["first_name", "last_name", "rating", "date_of_birth"]


class EmployeeRepository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    date_of_birth TEXT NOT NULL,
                    title TEXT,
                    image TEXT,
                    address TEXT,
                    country TEXT,
                    bio TEXT,
                    rating REAL,
                    fetched_at TEXT NOT NULL
                )
            """)
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def _row_to_employee(self, row: sqlite3.Row) -> Employee:
        return Employee(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            date_of_birth=date.fromisoformat(row["date_of_birth"]),
            title=row["title"] or "",
            image=row["image"] or "",
            address=row["address"] or "",
            country=row["country"] or "",
            bio=row["bio"] or "",
            rating=row["rating"] or 0.0,
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
        )

    def save_employees(self, employees: list[Employee]) -> int:
        """Save employees to database, replacing existing records."""
        if not employees:
            logger.warning("No employees to save")
            return 0

        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO employees
                (id, first_name, last_name, email, date_of_birth, title,
                 image, address, country, bio, rating, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.id,
                        e.first_name,
                        e.last_name,
                        e.email,
                        e.date_of_birth.isoformat(),
                        e.title,
                        e.image,
                        e.address,
                        e.country,
                        e.bio,
                        e.rating,
                        e.fetched_at.isoformat(),
                    )
                    for e in employees
                ],
            )
            conn.commit()

        logger.info(f"Saved {len(employees)} employees to database")
        return len(employees)

    def get_employees(
        self,
        country: str | None = None,
        min_rating: float | None = None,
        sort: SortField | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Employee]:
        """Query employees with optional filtering, sorting, and pagination."""
        query = "SELECT * FROM employees WHERE 1=1"
        params: list[Any] = []

        if country is not None:
            query += " AND country = ?"
            params.append(country)

        if min_rating is not None:
            query += " AND rating >= ?"
            params.append(min_rating)

        if sort is not None:
            valid_sorts = {"first_name", "last_name", "rating", "date_of_birth"}
            if sort in valid_sorts:
                query += f" ORDER BY {sort}"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        if offset is not None:
            if limit is None:
                query += " LIMIT -1"
            query += " OFFSET ?"
            params.append(offset)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        return [self._row_to_employee(row) for row in rows]

    def get_employee_by_id(self, employee_id: str) -> Employee | None:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM employees WHERE id = ?",
                (employee_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_employee(row)

    def count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM employees")
            return cursor.fetchone()[0]

    def clear(self) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM employees")
            conn.commit()
        logger.info("Cleared all employees from database")
