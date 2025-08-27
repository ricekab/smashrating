# smashrating
Generate historical skill ratings based on offline tournament performances

## Installation

### Development environment

TODO: Expand on this

1. Setup postgres database instance

```bash
docker compose up -d
```

2. Prepare Python environment and install application

Create a new virtual environment and install the required dependencies. Alternatively, you can also use `hatch` to manage the Python environment for you.

```bash
python -m venv venv

# Windows
venv\Scripts\activate.bat

# Linux
source venv/bin/activate

# Install in development mode
(venv)$ pip install -e .[dev]
```
3. Configure application

Copy `.env.example` to `.env`. Alternatively you can also configure the application using environment variables (TODO: Document there) or with CLI arguments (TODO: implement and document CLI usage below).

*Note: The database sample values match the values used for the postgres container created in step 1*

4. Initialize database schema

```bash
(venv)$ alembic upgrade head
```

## Usage

* [ ] TODO: Workflow brief
* [ ] TODO: config (env)
* [ ] TODO: CLI usage info

### Run tests

```bash
pytest tests/

coverage run -m pytest tests/
coverage report

hatch run test  # pytest only

hatch run test-cov  # run coverage command
hatch run test-report  # show coverage report

hatch run cov  # run test-cov followed by test-report
```