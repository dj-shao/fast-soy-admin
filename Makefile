# ============================================================
# FastSoyAdmin Makefile
# ============================================================

.DEFAULT_GOAL := help

# ── Backend ──────────────────────────────────────────────────

.PHONY: install
install: ## Install backend dependencies (uv sync)
	uv sync

.PHONY: run
run: ## Start backend dev server (port 9999)
	uv run python run.py

.PHONY: lint
lint: ## Ruff lint + format check
	uv run ruff check app/
	uv run ruff format --check app/

.PHONY: fmt
fmt: ## Ruff auto-fix + format
	uv run ruff check --fix app/
	uv run ruff format app/

.PHONY: typecheck
typecheck: ## basedpyright type check
	uv run basedpyright app

.PHONY: test
test: ## Run backend tests
	uv run pytest tests/ -v

.PHONY: check
check: fmt typecheck test ## Run all backend quality gates (format + typecheck + test)

# ── Database ─────────────────────────────────────────────────

.PHONY: initdb
initdb: ## First-time database init (migrations + migrate); pass ARGS=--force to re-init
	uv run python -m app.cli initdb $(ARGS)

.PHONY: makemigrations
makemigrations: ## Generate migration files from model changes
	uv run tortoise makemigrations

.PHONY: migrate
migrate: ## Apply pending migrations
	uv run tortoise migrate

.PHONY: mm
mm: makemigrations migrate ## Generate + apply migrations (shortcut)

.PHONY: dbhistory
dbhistory: ## Show migration history
	uv run tortoise history

# ── CLI ──────────────────────────────────────────────────────

.PHONY: cli-init
cli-init: ## Create a new business module skeleton (usage: make cli-init MOD=xxx)
	uv run python -m app.cli init $(MOD)

.PHONY: cli-gen
cli-gen: ## Generate backend code from models.py (usage: make cli-gen MOD=xxx)
	uv run python -m app.cli gen $(MOD)

.PHONY: cli-gen-web
cli-gen-web: ## Generate frontend code from models.py (usage: make cli-gen-web MOD=xxx [CN=中文名])
	uv run python -m app.cli gen-web $(MOD) $(if $(CN),--cn-name $(CN),)

.PHONY: cli-gen-all
cli-gen-all: cli-gen cli-gen-web ## Generate both backend and frontend code (usage: make cli-gen-all MOD=xxx [CN=中文名])

# ── Frontend ─────────────────────────────────────────────────

.PHONY: web-install
web-install: ## Install frontend dependencies
	cd web && pnpm install

.PHONY: web-dev
web-dev: ## Start frontend dev server (port 9527)
	cd web && pnpm dev

.PHONY: web-build
web-build: ## Production build frontend
	cd web && pnpm build

.PHONY: web-lint
web-lint: ## ESLint frontend
	cd web && pnpm lint

.PHONY: web-typecheck
web-typecheck: ## Vue-tsc type check frontend
	cd web && pnpm typecheck

.PHONY: web-check
web-check: web-lint web-typecheck ## Run all frontend quality gates

# ── Full Stack ───────────────────────────────────────────────

.PHONY: dev
dev: ## Start backend + frontend dev servers (parallel)
	@echo "Starting backend (port 9999) and frontend (port 9527)..."
	@trap 'kill 0' EXIT; uv run python run.py & (cd web && pnpm dev) & wait

.PHONY: install-all
install-all: install web-install ## Install all dependencies (backend + frontend)

.PHONY: check-all
check-all: check web-check ## Run all quality gates (backend + frontend)

# ── Docker ───────────────────────────────────────────────────

.PHONY: up
up: ## Docker compose up (nginx + fastapi + redis)
	docker compose up -d

.PHONY: down
down: ## Docker compose down
	docker compose down

.PHONY: logs
logs: ## Docker compose logs (follow)
	docker compose logs -f

# ── Help ─────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
