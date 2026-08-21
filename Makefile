.PHONY: format lint typecheck test check_release release

format:
	uv run python -m monoformat .

lint: typecheck
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest tests

check_release:
ifndef VERSION
	$(error VERSION is undefined)
endif

release: check_release
	git flow release start $(VERSION)
	sed -i 's/^version =.*/version = "$(VERSION)"/' pyproject.toml
	git add pyproject.toml
	git commit -m "Bump version to $(VERSION)"
	git flow release finish -m "Release $(VERSION)" $(VERSION) > /dev/null
