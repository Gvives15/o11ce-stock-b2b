# O11CE Stock B2B

## Overview
O11CE Stock B2B provides a simple Backend‑for‑Frontend (BFF) service for e‑commerce scenarios. It is built with the Django framework and is intended as a starting point for managing stock information in business‑to‑business environments.

## Prerequisites
- Python 3.10+
- [pip](https://pip.pypa.io/)
- [virtualenv](https://virtualenv.pypa.io/) (optional but recommended)
- [Django](https://www.djangoproject.com/) and any additional dependencies used by your apps

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
   pip install -r requirements.txt  # or install Django manually if requirements.txt is missing
   ```
4. **Run database migrations**
   ```bash
   python config/manage.py migrate
   ```
5. **Run the development server**
   ```bash
   python config/manage.py runserver
   ```
6. **Run tests**
   ```bash
   python config/manage.py test
   ```

## Architecture and Specifications
Dedicated architecture or specification documents are not yet included in this repository. Add links here once they are available.

## Contribution Guidelines
1. Fork the repository and create a feature branch for your work.
2. Follow existing code style and keep commits focused and descriptive.
3. Ensure tests run successfully before submitting a pull request.
4. Open a pull request against the default branch and describe your changes.
