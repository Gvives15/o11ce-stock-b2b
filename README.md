# O11CE Stock B2B

## Project Overview
O11CE Stock B2B provides a simple Backend-for-Frontend (BFF) service for e-commerce scenarios.
It is built with the Django framework and is intended as a starting point for managing stock information in business-to-business environments.

## Prerequisites
- Python 3.10+
- [pip](https://pip.pypa.io/)
- [virtualenv](https://virtualenv.pypa.io/) (optional but recommended)
- [Django](https://www.djangoproject.com/) and any additional dependencies used by your apps

## Environment Variables
The application is configured via environment variables. Copy `.env.example` to `.env` and update the values as needed.

Key variables include:
- `SECRET_KEY` – Django secret key.
- `DEBUG` – enable debug mode (`1` for development).
- `DATABASE_URL` – database connection string.
- `CORS_ALLOWED_ORIGINS` – comma-separated list of allowed origins.

## Local Setup
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd o11ce-stock-b2b
   ```
2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```
5. **Load seed data** (optional)
   ```bash
   python manage.py loaddata <path-to-fixture>.json
   ```
6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Docker Usage
Build and run the application with Docker:

```bash
docker build -t o11ce-stock-b2b .
docker run -p 8000:8000 --env-file .env o11ce-stock-b2b
```

Or using Docker Compose:

```bash
docker compose up --build
```

## Testing
Run the test suite with:

```bash
python manage.py test
```

## Architecture and Specifications
Dedicated architecture or specification documents are not yet included in this repository. Add links here once they are available.

## Contribution Guidelines
1. Fork the repository and create a feature branch for your work.
2. Follow existing code style and keep commits focused and descriptive.
3. Ensure tests run successfully before submitting a pull request.
4. Open a pull request against the default branch and describe your changes.

