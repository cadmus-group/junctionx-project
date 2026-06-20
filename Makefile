.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help install dev up down logs migrate seed reset-demo test lint typecheck build generate-contracts

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install JS (pnpm) and Python (pip + .venv)
	pnpm install
	./scripts/pip-install.sh

dev: ## Run web + api in dev mode
	pnpm dev

up: ## Start full Docker stack (postgres, migrate, api, worker, web, ml-lab)
	bash scripts/docker-up.sh

up-db: ## Start PostgreSQL/PostGIS only (local dev without containers for app code)
	docker compose up -d postgres
	@echo "Postgres is starting. Run 'make migrate' once it is healthy."

down: ## Stop all Docker Compose services
	bash scripts/docker-down.sh

logs: ## Tail Docker Compose logs
	bash scripts/docker-logs.sh

docker-seed: ## Seed demo data inside the worker container
	bash scripts/docker-seed.sh

docker-build: ## Build all Docker images without starting
	docker compose build

migrate: ## Apply database migrations
	pnpm db:migrate

seed: ## Seed deterministic demo data
	pnpm db:seed

reset-demo: ## Reset and regenerate the deterministic demo
	pnpm demo:reset

test: ## Run all tests
	pnpm test

lint: ## Lint all workspaces
	pnpm lint

typecheck: ## Typecheck all workspaces
	pnpm typecheck

build: ## Build all workspaces
	pnpm build

generate-contracts: ## Regenerate typed API contracts from OpenAPI
	pnpm generate:contracts
