.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help install dev up down logs migrate seed reset-demo test lint typecheck build generate-contracts

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install JS (pnpm) and Python (uv) dependencies
	pnpm install
	uv sync --all-packages

dev: ## Run web + api in dev mode
	pnpm dev

up: ## Start docker compose services (postgres, api, worker)
	docker compose up -d postgres
	@echo "Postgres is starting. Run 'make migrate' once it is healthy."

down: ## Stop docker compose services
	docker compose down

logs: ## Tail docker compose logs
	docker compose logs -f

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
