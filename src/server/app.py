"""FastAPI HTTP service for serving employee data."""

import csv
import io
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.config import get_settings
from src.models import EmployeeResponse
from src.storage.repository import EmployeeRepository, SortField

app = FastAPI(
    title="Employee API",
    description="HTTP service for querying locally stored employee data",
    version="0.1.0",
)


def get_repository() -> EmployeeRepository:
    settings = get_settings()
    return EmployeeRepository(settings.db_path)


@app.get("/employees", response_model=list[EmployeeResponse])
def get_employees(
    repository: Annotated[EmployeeRepository, Depends(get_repository)],
    country: str | None = Query(None, description="Filter by exact country match"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Minimum rating threshold"),
    sort: SortField | None = Query(None, description="Sort by field"),
    format: Literal["json", "csv"] = Query("json", description="Response format"),
    limit: int | None = Query(None, ge=1, le=1000, description="Maximum results"),
    offset: int | None = Query(None, ge=0, description="Number of results to skip"),
) -> list[EmployeeResponse] | StreamingResponse:
    employees = repository.get_employees(
        country=country,
        min_rating=min_rating,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    if format == "csv":
        return _employees_to_csv_response(employees)

    return [
        EmployeeResponse(
            id=e.id,
            first_name=e.first_name,
            last_name=e.last_name,
            email=e.email,
            date_of_birth=e.date_of_birth,
            title=e.title,
            image=e.image,
            address=e.address,
            country=e.country,
            bio=e.bio,
            rating=e.rating,
            fetched_at=e.fetched_at,
        )
        for e in employees
    ]


@app.get("/employees/{employee_id}", response_model=EmployeeResponse)
def get_employee_by_id(
    employee_id: str,
    repository: Annotated[EmployeeRepository, Depends(get_repository)],
) -> EmployeeResponse:
    employee = repository.get_employee_by_id(employee_id)

    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    return EmployeeResponse(
        id=employee.id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        email=employee.email,
        date_of_birth=employee.date_of_birth,
        title=employee.title,
        image=employee.image,
        address=employee.address,
        country=employee.country,
        bio=employee.bio,
        rating=employee.rating,
        fetched_at=employee.fetched_at,
    )


def _employees_to_csv_response(employees: list) -> StreamingResponse:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "first_name", "last_name", "email", "date_of_birth",
        "title", "image", "address", "country", "bio", "rating", "fetched_at"
    ])

    for e in employees:
        writer.writerow([
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
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )
