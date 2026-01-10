# Claude Code API - Makefile
# Beautiful CLI for development and testing (using uv)

.PHONY: help install dev server stop status test test-quick test-full test-gist clean lint format typecheck
.PHONY: docker-build docker-run docker-stop docker-test docker-logs docker-shell docker-clean
.PHONY: kamal-setup kamal-deploy kamal-logs kamal-console kamal-rollback kamal-details
.PHONY: chat chat-web chat-web-stop

# Colors for pretty output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BOLD := \033[1m
DIM := \033[2m
RESET := \033[0m

# Server settings (using uncommon ports to avoid conflicts)
PORT := 7742
PID_FILE := .server.pid
CHAT_PORT := 7743
CHAT_PID_FILE := .chat.pid

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
	@echo "$(BOLD)Kamal Deploy:$(RESET)"
	@echo "  $(GREEN)make kamal-setup$(RESET)   Initial server setup (first time)"
	@echo "  $(GREEN)make kamal-deploy$(RESET)  Deploy latest changes"
	@echo "  $(GREEN)make kamal-logs$(RESET)    Tail production logs"
	@echo "  $(GREEN)make kamal-console$(RESET) SSH into production container"
	@echo "  $(GREEN)make kamal-rollback$(RESET) Rollback to previous version"
	@echo "  $(GREEN)make kamal-details$(RESET) Show deployment details"
	@echo ""
	@echo "$(BOLD)Examples:$(RESET)"
	@echo "  $(GREEN)make chat$(RESET)         Interactive terminal chat"
	@echo "  $(GREEN)make chat-web$(RESET)     Start web chat (port $(CHAT_PORT))"
	@echo "  $(GREEN)make chat-web-stop$(RESET) Stop web chat server"
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
# Kamal Deployment (requires: gem install kamal)
# Docs: https://kamal-deploy.org/docs/
#───────────────────────────────────────────────────────────────────────────────

kamal-setup:
	@echo "$(CYAN)Setting up Kamal on server (first-time deployment)...$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────$(RESET)"
	@if ! command -v kamal >/dev/null 2>&1; then \
		echo "$(RED)Kamal not found. Install with: gem install kamal$(RESET)"; \
		exit 1; \
	fi
	@if [ ! -f .kamal/secrets ]; then \
		echo "$(YELLOW)⚠ .kamal/secrets not found$(RESET)"; \
		echo "$(DIM)  Copy .kamal/secrets.example to .kamal/secrets$(RESET)"; \
		echo "$(DIM)  Fill in KAMAL_REGISTRY_PASSWORD and CLAUDE_CODE_OAUTH_TOKEN$(RESET)"; \
		exit 1; \
	fi
	kamal setup
	@echo ""
	@echo "$(GREEN)✓ Kamal setup complete$(RESET)"

kamal-deploy:
	@echo "$(CYAN)Deploying to production...$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────$(RESET)"
	@if ! command -v kamal >/dev/null 2>&1; then \
		echo "$(RED)Kamal not found. Install with: gem install kamal$(RESET)"; \
		exit 1; \
	fi
	kamal deploy
	@echo ""
	@echo "$(GREEN)✓ Deployment complete$(RESET)"

kamal-logs:
	@echo "$(CYAN)Production logs (Ctrl+C to exit)$(RESET)"
	@kamal app logs -f 2>/dev/null || echo "$(YELLOW)Could not connect to production$(RESET)"

kamal-console:
	@echo "$(CYAN)Opening shell in production container...$(RESET)"
	@kamal app exec -i /bin/bash 2>/dev/null || echo "$(YELLOW)Could not connect to production$(RESET)"

kamal-rollback:
	@echo "$(CYAN)Rolling back to previous version...$(RESET)"
	@kamal rollback
	@echo "$(GREEN)✓ Rollback complete$(RESET)"

kamal-details:
	@echo ""
	@echo "$(BOLD)Kamal Deployment Details$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────$(RESET)"
	@kamal details 2>/dev/null || echo "$(YELLOW)Could not fetch details$(RESET)"

#───────────────────────────────────────────────────────────────────────────────
# Examples (Streaming Chat)
#───────────────────────────────────────────────────────────────────────────────

chat:
	@echo "$(CYAN)Starting interactive chat...$(RESET)"
	@echo "$(DIM)Type 'quit' to exit$(RESET)"
	@echo ""
	@uv run python examples/streaming_chat.py

chat-web:
	@echo "$(CYAN)Starting web chat server on port $(CHAT_PORT)...$(RESET)"
	@if [ -f $(CHAT_PID_FILE) ] && kill -0 $$(cat $(CHAT_PID_FILE)) 2>/dev/null; then \
		echo "$(YELLOW)Web chat already running (PID: $$(cat $(CHAT_PID_FILE)))$(RESET)"; \
	else \
		uv sync --extra examples > /dev/null 2>&1; \
		uv run uvicorn examples.streaming_web_chat:app --host 0.0.0.0 --port $(CHAT_PORT) & \
		echo $$! > $(CHAT_PID_FILE); \
		sleep 2; \
		echo "$(GREEN)✓ Web chat started (PID: $$(cat $(CHAT_PID_FILE)))$(RESET)"; \
		echo "$(DIM)  Open: http://localhost:$(CHAT_PORT)$(RESET)"; \
	fi

chat-web-stop:
	@if [ -f $(CHAT_PID_FILE) ]; then \
		PID=$$(cat $(CHAT_PID_FILE)); \
		if kill -0 $$PID 2>/dev/null; then \
			kill $$PID; \
			echo "$(GREEN)✓ Web chat stopped (PID: $$PID)$(RESET)"; \
		else \
			echo "$(YELLOW)Web chat not running$(RESET)"; \
		fi; \
		rm -f $(CHAT_PID_FILE); \
	else \
		echo "$(YELLOW)No PID file found$(RESET)"; \
		pkill -f "uvicorn examples.streaming_web_chat" 2>/dev/null && echo "$(GREEN)Killed orphan process$(RESET)" || echo "$(DIM)No server found$(RESET)"; \
	fi

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
