SHELL := /bin/bash
COMPOSE := docker compose

.PHONY: help up down logs install migrate fresh seed demo test test-api test-intelligence \
        test-web web-dev web-build check-routes check-migrations benchmark benchmark-afriswitch benchmark-ablation capture lint

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "\033[36m%-22s\033[0m %s\n",$$1,$$2}'

up: ## Start the full stack
	$(COMPOSE) up -d --build

down: ## Stop the stack
	$(COMPOSE) down

logs: ## Tail logs
	$(COMPOSE) logs -f api intelligence web

install: ## Install deps + migrate + seed
	$(COMPOSE) exec api composer install
	cd apps/web && npm install
	$(COMPOSE) exec api php artisan key:generate
	$(COMPOSE) exec api php artisan migrate --force
	$(COMPOSE) exec api php artisan db:seed --force

migrate: ## Run migrations
	$(COMPOSE) exec api php artisan migrate --force

fresh: ## Drop + migrate + seed
	$(COMPOSE) exec api php artisan migrate:fresh --seed --force

seed: ## Seed reference data
	$(COMPOSE) exec api php artisan db:seed --force

demo: ## Build the deterministic demo case from fixtures
	$(COMPOSE) exec api php artisan wunzi:demo-case

check-routes: ## Verify every HTTP boundary agrees on its paths
	python3 scripts/check_routes.py

check-migrations: ## Catch PostgreSQL-only migration ordering hazards
	python3 scripts/check_migrations.py

test: check-routes check-migrations test-api test-intelligence test-web ## Run every suite

test-api:
	$(COMPOSE) exec api php artisan test

web-dev: ## Run the Next.js app against a local API
	cd apps/web && npm run dev

web-build: ## Production build of the Next.js app
	cd apps/web && npm run build

test-web: ## Typecheck the frontend
	cd apps/web && npm run typecheck

test-intelligence:
	$(COMPOSE) exec intelligence pytest -q

benchmark: ## Run the 4-ASR holdout benchmark and compute the Sponsor Outcome Delta
	$(COMPOSE) exec intelligence python -m app.benchmark.cli run \
		--dataset $${DATASET_VERSION:-dataset-v1} \
		--split holdout \
		--providers sahara,whisper,model_b,model_c \
		--out /benchmark/reports

benchmark-afriswitch: ## Tier 1 — WER/CER + code-switch metrics on AfriSwitch Kinyarwanda
	$(COMPOSE) exec intelligence python -m app.benchmark.afriswitch_cli run \
		--config kinyarwanda --limit 200 \
		--providers sahara,whisper,model_b,model_c \
		--out /benchmark/reports

benchmark-ablation: ## Same run with the Critical Speech Guard disabled
	$(COMPOSE) exec intelligence python -m app.benchmark.cli run \
		--split holdout --no-guard \
		--providers sahara,whisper,model_b,model_c \
		--out /benchmark/reports

capture: ## Capture authentic provider output (requires live API keys)
	$(COMPOSE) exec -e WUNZI_MODE=live intelligence \
		python -m app.benchmark.capture --providers sahara,whisper,model_b,model_c

lint:
	$(COMPOSE) exec intelligence python -m compileall -q app
	cd apps/web && npm run lint
