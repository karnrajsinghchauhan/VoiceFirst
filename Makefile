# Agoda Voice. Every target runs from the repo root.
SHELL := /bin/bash
export UV_SYSTEM_CERTS := 1
unexport UV_NATIVE_TLS
UV := cd server && uv run --quiet
PG_URL ?= postgresql+psycopg://postgres:postgres@localhost:5432/agoda_voice_test

.PHONY: up down gen check lint typecheck test e2e eval eval-audio load chaos seed demo report web-check

up:
	docker compose -f deploy/docker-compose.yml up -d --wait

down:
	docker compose -f deploy/docker-compose.yml down

gen:
	scripts/gen_contracts.sh "$(CURDIR)/server/app/contracts/generated" "$(CURDIR)/web/src/contracts"

lint:
	$(UV) ruff check app tests ../evals ../scripts
	$(UV) ruff format --check app tests ../evals ../scripts
	$(UV) lint-imports

typecheck:
	$(UV) mypy app

test:
	$(UV) pytest -q -n 4 -m "not e2e"

web-check:
	cd web && npm run --silent typecheck && npm run --silent lint

check: lint typecheck test web-check
	scripts/check_contract_drift.sh

e2e:
	AV_TEST_DATABASE_URL=$(PG_URL) $(UV) pytest -q -m e2e

eval:
	$(UV) python ../evals/run_evals.py --mode text

eval-audio:
	$(UV) python ../evals/run_evals.py --mode audio

load:
	$(UV) python -m app.simulator.load --sessions 200

chaos:
	$(UV) pytest -q tests/chaos

seed:
	$(UV) python ../scripts/seed_demo.py

demo:
	$(UV) python -m app.voice.demo

report:
	$(UV) python ../evals/run_evals.py --mode text --report-only
