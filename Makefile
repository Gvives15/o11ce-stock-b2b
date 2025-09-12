.PHONY: install run lint format test makemigrations migrate

install:
	pip install -r requirements.txt

run:
	python manage.py runserver

lint:
	pylint $(shell find . -name "*.py" -not -path "./.venv/*")

format:
	black .

test:
	pytest

makemigrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate
