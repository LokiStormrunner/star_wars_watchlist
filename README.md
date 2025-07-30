# FastAPI Project

This is a basic FastAPI project managed with Poetry.

## Setup

1. Install dependencies:
   ```bash
   make install
   ```

2. Run the server:
   ```bash
   make run
   ```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) to see the API.

## Other Commands
- `make test`: Run tests (requires pytest)
- `make lint`: Lint code (requires flake8)
- `make clean`: Remove cache files

## API Endpoints
- `GET /`: Returns a welcome message.
