.PHONY: test lint serve clean

test: ## Run the test suite
	pytest tests/

lint: ## Run linter
	ruff check .

serve: ## Start the dev server
	sample-cli serve

clean: ## Remove build artifacts
	rm -rf dist build *.egg-info
