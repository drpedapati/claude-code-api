# Claude Code API - Makefile
# Beautiful CLI for development and testing (using uv)

.PHONY: help install dev server stop status test test-quick test-full test-gist clean lint format typecheck
.PHONY: docker-build docker-run docker-stop docker-test docker-logs docker-shell docker-clean

# Colors for pretty output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BOLD := \033[1m
DIM := \033[2m
RESET := \033[0m

# Server settings
PORT := 8000
PID_FILE := .server.pid

# Docker settings
IMAGE_NAME := claude-code-api
IMAGE_TAG := latest
CONTAINER_NAME := claude-code-api

#───────────────────────────────────────────────────────────────────────────────
# Help
#───────────────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "$(BOLD)$(CYAN)Claude Code API$(RESET) $(DIM)(using uv)$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────────────────────────$(RESET)"
	@echo ""
	@echo "$(BOLD)Local Server:$(RESET)"
	@echo "  $(GREEN)make server$(RESET)       Start the API server (port $(PORT))"
	@echo "  $(GREEN)make stop$(RESET)         Stop the running server"
	@echo "  $(GREEN)make status$(RESET)       Check server status"
	@echo ""
	@echo "$(BOLD)Docker:$(RESET)"
	@echo "  $(GREEN)make docker-build$(RESET) Build the Docker image"
	@echo "  $(GREEN)make docker-run$(RESET)   Run container (port $(PORT))"
	@echo "  $(GREEN)make docker-stop$(RESET)  Stop and remove container"
	@echo "  $(GREEN)make docker-test$(RESET)  Build and test container"
	@echo "  $(GREEN)make docker-logs$(RESET)  Tail container logs"
	@echo "  $(GREEN)make docker-shell$(RESET) Open shell in container"
	@echo ""
	@echo "$(BOLD)Testing:$(RESET)"
	@echo "  $(GREEN)make test$(RESET)         Run all tests"
	@echo "  $(GREEN)make test-quick$(RESET)   Run unit tests only (no CLI)"
	@echo "  $(GREEN)make test-gist$(RESET)    Run SDK spec tests (beautiful output)"
	@echo ""
	@echo "$(BOLD)Development:$(RESET)"
	@echo "  $(GREEN)make install$(RESET)      Install package"
	@echo "  $(GREEN)make dev$(RESET)          Install with dev dependencies"
	@echo "  $(GREEN)make lint$(RESET)         Run linter"
	@echo "  $(GREEN)make format$(RESET)       Format code"
	@echo "  $(GREEN)make typecheck$(RESET)    Run type checker"
	@echo "  $(GREEN)make clean$(RESET)        Clean build artifacts"
	@echo ""

#───────────────────────────────────────────────────────────────────────────────
# Installation (using uv)
#───────────────────────────────────────────────────────────────────────────────

install:
	@echo "$(CYAN)Installing claude-code-api with uv...$(RESET)"
	uv pip install -e .

dev:
	@echo "$(CYAN)Installing with all dependencies...$(RESET)"
	uv pip install -e ".[all]"

#───────────────────────────────────────────────────────────────────────────────
# Local Server Management
#───────────────────────────────────────────────────────────────────────────────

server:
	@echo "$(CYAN)Starting server on port $(PORT)...$(RESET)"
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "$(YELLOW)Server already running (PID: $$(cat $(PID_FILE)))$(RESET)"; \
	else \
		uv run uvicorn claude_code_api.server:app --host 0.0.0.0 --port $(PORT) & \
		echo $$! > $(PID_FILE); \
		sleep 2; \
		echo "$(GREEN)Server started (PID: $$(cat $(PID_FILE)))$(RESET)"; \
		echo "$(DIM)API docs: http://localhost:$(PORT)/docs$(RESET)"; \
	fi

stop:
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "$(GREEN)Server stopped (PID: $$PID)$(RESET)"; \
		else \
			echo "$(YELLOW)Server not running$(RESET)"; \
		fi; \
		rm -f $(PID_FILE); \
	else \
		echo "$(YELLOW)No PID file found. Checking for orphan processes...$(RESET)"; \
		pkill -f "uvicorn claude_code_api" 2>/dev/null && echo "$(GREEN)Killed orphan server$(RESET)" || echo "$(DIM)No server found$(RESET)"; \
	fi

status:
	@echo ""
	@echo "$(BOLD)Server Status$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────$(RESET)"
	@if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null; then \
		echo "$(GREEN)● Local$(RESET) Running (PID: $$(cat $(PID_FILE)))"; \
	else \
		echo "$(DIM)● Local$(RESET) Stopped"; \
	fi
	@if docker ps --format '{{.Names}}' | grep -q "^$(CONTAINER_NAME)$$" 2>/dev/null; then \
		echo "$(GREEN)● Docker$(RESET) Running ($(CONTAINER_NAME))"; \
	else \
		echo "$(DIM)● Docker$(RESET) Stopped"; \
	fi
	@echo ""

logs:
	@echo "$(CYAN)Server logs (Ctrl+C to exit)$(RESET)"
	@tail -f /tmp/claude-code-api.log 2>/dev/null || echo "$(YELLOW)No log file found$(RESET)"

#───────────────────────────────────────────────────────────────────────────────
# Docker Commands
#───────────────────────────────────────────────────────────────────────────────

docker-build:
	@echo "$(CYAN)Building Docker image...$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────$(RESET)"
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .
	@echo ""
	@echo "$(GREEN)✓ Built $(IMAGE_NAME):$(IMAGE_TAG)$(RESET)"
	@docker images $(IMAGE_NAME):$(IMAGE_TAG) --format "  Size: {{.Size}}"

docker-run:
	@echo "$(CYAN)Starting container...$(RESET)"
	@if docker ps --format '{{.Names}}' | grep -q "^$(CONTAINER_NAME)$$"; then \
		echo "$(YELLOW)Container already running$(RESET)"; \
	else \
		if [ -z "$${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then \
			echo "$(YELLOW)⚠ CLAUDE_CODE_OAUTH_TOKEN not set$(RESET)"; \
			echo "$(DIM)  Generate with: claude setup-token$(RESET)"; \
			echo "$(DIM)  Then: CLAUDE_CODE_OAUTH_TOKEN=... make docker-run$(RESET)"; \
		fi; \
		docker run -d \
			--name $(CONTAINER_NAME) \
			-p $(PORT):8000 \
			-v claude-code-data:/home/appuser/.claude \
			-e CLAUDE_CODE_OAUTH_TOKEN=$${CLAUDE_CODE_OAUTH_TOKEN:-} \
			$(IMAGE_NAME):$(IMAGE_TAG); \
		sleep 2; \
		echo "$(GREEN)✓ Container started$(RESET)"; \
		echo "$(DIM)  API: http://localhost:$(PORT)$(RESET)"; \
		echo "$(DIM)  Docs: http://localhost:$(PORT)/docs$(RESET)"; \
	fi

docker-stop:
	@echo "$(CYAN)Stopping container...$(RESET)"
	@docker stop $(CONTAINER_NAME) 2>/dev/null || true
	@docker rm $(CONTAINER_NAME) 2>/dev/null || true
	@echo "$(GREEN)✓ Container stopped$(RESET)"

docker-test: docker-build
	@echo ""
	@echo "$(CYAN)Testing container...$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────$(RESET)"
	@# Start container
	@docker rm -f $(CONTAINER_NAME)-test 2>/dev/null || true
	@docker run -d --name $(CONTAINER_NAME)-test -p 8888:8000 $(IMAGE_NAME):$(IMAGE_TAG)
	@sleep 3
	@# Health check
	@echo -n "  Health check: "
	@if curl -sf http://localhost:8888/health > /dev/null; then \
		echo "$(GREEN)✓ passed$(RESET)"; \
	else \
		echo "$(RED)✗ failed$(RESET)"; \
		docker logs $(CONTAINER_NAME)-test; \
		docker rm -f $(CONTAINER_NAME)-test; \
		exit 1; \
	fi
	@# Status check
	@echo -n "  Status check: "
	@if curl -sf http://localhost:8888/llm/status | grep -q '"available"'; then \
		echo "$(GREEN)✓ passed$(RESET)"; \
	else \
		echo "$(YELLOW)⚠ Claude CLI not configured$(RESET)"; \
	fi
	@# Cleanup
	@docker rm -f $(CONTAINER_NAME)-test > /dev/null
	@echo ""
	@echo "$(GREEN)✓ Container tests passed$(RESET)"

docker-logs:
	@echo "$(CYAN)Container logs (Ctrl+C to exit)$(RESET)"
	@docker logs -f $(CONTAINER_NAME) 2>/dev/null || echo "$(YELLOW)Container not running$(RESET)"

docker-shell:
	@echo "$(CYAN)Opening shell in container...$(RESET)"
	@docker exec -it $(CONTAINER_NAME) /bin/bash 2>/dev/null || echo "$(YELLOW)Container not running$(RESET)"

docker-clean:
	@echo "$(CYAN)Cleaning Docker resources...$(RESET)"
	@docker stop $(CONTAINER_NAME) 2>/dev/null || true
	@docker rm $(CONTAINER_NAME) 2>/dev/null || true
	@docker rmi $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned$(RESET)"

#───────────────────────────────────────────────────────────────────────────────
# Testing (using uv run)
#───────────────────────────────────────────────────────────────────────────────

test:
	@echo "$(CYAN)Running all tests...$(RESET)"
	uv run pytest -v

test-quick:
	@echo "$(CYAN)Running unit tests (no CLI required)...$(RESET)"
	uv run pytest -v -m "not integration"

test-full:
	@echo "$(CYAN)Running full test suite with integration tests...$(RESET)"
	uv run pytest -v -m "integration"

test-gist:
	@uv run python scripts/test_sdk_spec.py

#───────────────────────────────────────────────────────────────────────────────
# Code Quality (using uv run)
#───────────────────────────────────────────────────────────────────────────────

lint:
	@echo "$(CYAN)Running linter...$(RESET)"
	uv run ruff check .

format:
	@echo "$(CYAN)Formatting code...$(RESET)"
	uv run ruff format .

typecheck:
	@echo "$(CYAN)Running type checker...$(RESET)"
	uv run mypy claude_code_api

#───────────────────────────────────────────────────────────────────────────────
# Cleanup
#───────────────────────────────────────────────────────────────────────────────

clean:
	@echo "$(CYAN)Cleaning build artifacts...$(RESET)"
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -f $(PID_FILE)
	@echo "$(GREEN)✓ Clean$(RESET)"
