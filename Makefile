run:
	uv run python main.py

lint:
	uv run ruff check .

format:
	uv run ruff format .

## Remove all build, test, coverage and Python artifacts
clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
