install:
	poetry install

run:
	poetry run uvicorn main:app --reload

test:
	poetry run pytest

lint:
	poetry run flake8 .

clean:
	rm -rf __pycache__ .pytest_cache
