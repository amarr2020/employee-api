# Employee API

A Python application that authenticates to an external API, fetches employee data, stores it locally in SQLite, and exposes it via an HTTP service.

## Features

- Authenticate with external API using OAuth-style token flow
- Fetch and validate employee data with Pydantic v2
- Store employees in SQLite with automatic schema management
- HTTP API with filtering, sorting, and pagination
- CSV and JSON export support
- Resilient HTTP client with retry logic and exponential backoff
- Token caching with automatic expiry handling
- Async support for better performance
- Seed script for quick database population

## Requirements

- Python 3.11+
- Dependencies listed in `requirements.txt` or `pyproject.toml`

## Setup

### Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Using Poetry

```bash
poetry install
```

### Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required variables:

| Variable | Description |
|----------|-------------|
| `API_BASE_URL` | Base URL of the external API (default: `http://localhost`) |
| `API_CLIENT_ID` | OAuth client ID |
| `API_CLIENT_SECRET` | OAuth client secret |
| `API_USERNAME` | API username |
| `API_PASSWORD` | API password |
| `DATABASE_URL` | SQLite database URL (default: `sqlite:///./employees.db`) |

## Usage

### Running the Mock Server (for Development/Testing)

The application includes a mock test server that simulates the external API. This allows you to test the full flow without needing an actual external server.

**Start the mock server:**

```bash
python -m src.main mock
```

With custom port:

```bash
python -m src.main mock --port 8001
```

The mock server provides:
- `POST /api/token/` - Returns authentication token (accepts any non-empty credentials)
- `GET /api/employee/list/` - Returns sample employee data (requires `Access-Token` header)

**Configure your `.env` to use the mock server:**

```bash
API_BASE_URL=http://localhost:8001
API_CLIENT_ID=test
API_CLIENT_SECRET=test
API_USERNAME=test
API_PASSWORD=test
```

### Fetch and Store Employees

Fetch employees from the API and store them locally:

```bash
python -m src.main fetch
```

With optional export:

```bash
python -m src.main fetch --export-json employees.json --export-csv employees.csv
```

### Async Fetch (Alternative)

Use the async version for better performance with concurrent operations:

```bash
python -m src.main async-fetch
```

With optional export:

```bash
python -m src.main async-fetch --export-json employees.json --export-csv employees.csv
```

### Seed Script (Quick Start)

The seed script automatically starts the mock server, fetches employees, stores them in the database, and exports sample files:

```bash
python scripts/seed.py
```

This will:
1. Start the mock server on port 8001
2. Fetch employees using the async client
3. Store them in `employees.db`
4. Export to `samples/employees.json` and `samples/employees.csv`
5. Stop the mock server

This is the easiest way to populate the database for testing.

### Run HTTP Server

Start the HTTP API server:

```bash
python -m src.main serve
```

With custom host/port:

```bash
python -m src.main serve --host 0.0.0.0 --port 8000
```

Or using uvicorn directly:

```bash
uvicorn src.server.app:app --reload
```

### API Endpoints

#### GET /employees

Query locally stored employees.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `country` | string | Filter by exact country match |
| `min_rating` | float | Filter by minimum rating (0-5) |
| `sort` | string | Sort by: `first_name`, `last_name`, `rating`, `date_of_birth` |
| `format` | string | Response format: `json` (default) or `csv` |
| `limit` | int | Maximum results (1-1000) |
| `offset` | int | Number of results to skip |

**Examples:**

```bash
# Get all employees
curl http://localhost:8000/employees

# Filter by country
curl "http://localhost:8000/employees?country=USA"

# Filter by rating and sort
curl "http://localhost:8000/employees?min_rating=4.0&sort=rating"

# Pagination
curl "http://localhost:8000/employees?limit=10&offset=20"

# Export as CSV
curl "http://localhost:8000/employees?format=csv" > employees.csv
```

#### GET /employees/{id}

Get a single employee by ID.

```bash
curl http://localhost:8000/employees/8c8c13b6-35ed-3ffb-92d5-c438825df67f
```

### OpenAPI Documentation

When the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

## Code Quality

```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type checking
mypy src
```

## Architecture

```
src/
├── config.py                    # Environment configuration
├── models.py                    # Pydantic models (Token, Employee)
├── auth/
│   ├── strategy.py              # Auth header abstraction (Access-Token vs Bearer)
│   ├── token_client.py          # Sync token fetching with caching
│   └── async_token_client.py    # Async token fetching with caching
├── client/
│   ├── employee_client.py       # Sync API client with retries
│   └── async_employee_client.py # Async API client with retries
├── storage/
│   └── repository.py            # SQLite repository
├── server/
│   └── app.py                   # FastAPI application (serves stored data)
├── mock_server/
│   ├── app.py                   # Mock API server (simulates external API)
│   └── data.py                  # Sample employee data
└── main.py                      # CLI entry points

scripts/
└── seed.py                      # Seed script (auto-populates database)
```

### Key Design Decisions

1. **Auth Header Abstraction**: The external API uses a non-standard `Access-Token` header. The `AuthHeaderStrategy` interface allows easy switching to `Authorization: Bearer` by changing a config value.

2. **Pydantic v2 Validation**: Employee data is validated on ingestion. Invalid records are logged and skipped, not causing the entire fetch to fail.

3. **Resilient HTTP Client**: Uses `tenacity` for automatic retries with exponential backoff on transient errors.

4. **Token Caching**: Tokens are cached and reused until near expiry, reducing unnecessary authentication requests.

5. **Repository Pattern**: SQLite access is encapsulated in a repository class, making it easy to swap storage backends.

6. **Local-First Serving**: The HTTP API reads from local storage only, never proxying to the external API on each request.

## Sample Data

Sample output files are provided in `samples/`:
- `samples/employees.json` - JSON format
- `samples/employees.csv` - CSV format
