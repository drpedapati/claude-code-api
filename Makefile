# Claude Code API - Makefile
# Beautiful CLI for development and testing (using uv)

.PHONY: help install dev server stop status test test-quick test-full test-gist clean lint format typecheck

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

#───────────────────────────────────────────────────────────────────────────────
# Help
#───────────────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "$(BOLD)$(CYAN)Claude Code API$(RESET) $(DIM)(using uv)$(RESET)"
	@echo "$(DIM)─────────────────────────────────────────────────────────────$(RESET)"
	@echo ""
	@echo "$(BOLD)Server Commands:$(RESET)"
	@echo "  $(GREEN)make server$(RESET)      Start the API server (port $(PORT))"
	@echo "  $(GREEN)make stop$(RESET)        Stop the running server"
	@echo "  $(GREEN)make status$(RESET)      Check server status"
	@echo "  $(GREEN)make logs$(RESET)        Tail server logs"
	@echo ""
	@echo "$(BOLD)Testing:$(RESET)"
	@echo "  $(GREEN)make test$(RESET)        Run all tests"
	@echo "  $(GREEN)make test-quick$(RESET)  Run unit tests only (no CLI)"
	@echo "  $(GREEN)make test-gist$(RESET)   Run SDK spec tests (beautiful output)"
	@echo ""
	@echo "$(BOLD)Development:$(RESET)"
	@echo "  $(GREEN)make install$(RESET)     Install package"
	@echo "  $(GREEN)make dev$(RESET)         Install with dev dependencies"
	@echo "  $(GREEN)make lint$(RESET)        Run linter"
	@echo "  $(GREEN)make format$(RESET)      Format code"
	@echo "  $(GREEN)make typecheck$(RESET)   Run type checker"
	@echo "  $(GREEN)make clean$(RESET)       Clean build artifacts"
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
# Server Management
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
		echo "$(GREEN)● Running$(RESET) (PID: $$(cat $(PID_FILE)))"; \
		curl -s http://localhost:$(PORT)/health | python3 -m json.tool 2>/dev/null || echo "$(YELLOW)Not responding$(RESET)"; \
	else \
		echo "$(RED)● Stopped$(RESET)"; \
	fi
	@echo ""

logs:
	@echo "$(CYAN)Server logs (Ctrl+C to exit)$(RESET)"
	@tail -f /tmp/claude-code-api.log 2>/dev/null || echo "$(YELLOW)No log file found$(RESET)"

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
	@echo "$(GREEN)Clean!$(RESET)"
