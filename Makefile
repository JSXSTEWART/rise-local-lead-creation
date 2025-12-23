# Rise Local Lead Creation Pipeline - Makefile
# Build automation for the entire system

.PHONY: help install install-dev install-all build up down restart logs health test clean dashboard

# Default target
help:
	@echo "Rise Local Lead Creation Pipeline - Build Commands"
	@echo "=================================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install          - Install Python dependencies (root + rise_pipeline)"
	@echo "  make install-dev      - Install with development dependencies"
	@echo "  make install-all      - Install all dependencies (Python + Node.js)"
	@echo ""
	@echo "Docker Services:"
	@echo "  make build            - Build all Docker service images"
	@echo "  make up               - Start all Docker services"
	@echo "  make down             - Stop all Docker services"
	@echo "  make restart          - Restart all Docker services"
	@echo "  make logs             - View Docker service logs"
	@echo ""
	@echo "Health & Testing:"
	@echo "  make health           - Check health of all services"
	@echo "  make test             - Run all Python tests"
	@echo "  make test-services    - Test all Docker service endpoints"
	@echo ""
	@echo "Pipeline Operations:"
	@echo "  make prequalify       - Run pre-qualification (FREE scrapers)"
	@echo "  make phase2           - Run Phase 2 intelligence gathering"
	@echo "  make dashboard        - Start the web dashboard"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            - Remove temporary files and caches"
	@echo "  make clean-all        - Remove all build artifacts and Docker volumes"

# Install Python dependencies
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	pip install -r rise_pipeline/requirements.txt
	@echo "✓ Python dependencies installed"

install-dev: install
	@echo "Installing development dependencies..."
	pip install pytest pytest-asyncio black flake8 mypy
	@echo "✓ Development dependencies installed"

install-all: install
	@echo "Installing Node.js dependencies..."
	cd marketing/landing_pages && npm install
	@echo "✓ All dependencies installed"

# Docker service management
build:
	@echo "Building Docker service images..."
	cd custom_tools && docker compose build
	@echo "✓ Docker images built"

up:
	@echo "Starting Docker services..."
	cd custom_tools && docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@make health
	@echo "✓ Docker services started"

down:
	@echo "Stopping Docker services..."
	cd custom_tools && docker compose down
	@echo "✓ Docker services stopped"

restart: down up

logs:
	cd custom_tools && docker compose logs -f

# Health checks for all services
health:
	@echo "Checking service health..."
	@echo -n "TDLR Scraper (8001): "
	@curl -sf http://localhost:8001/health > /dev/null && echo "✓ OK" || echo "✗ FAILED"
	@echo -n "BBB Scraper (8002): "
	@curl -sf http://localhost:8002/health > /dev/null && echo "✓ OK" || echo "✗ FAILED"
	@echo -n "PageSpeed API (8003): "
	@curl -sf http://localhost:8003/health > /dev/null && echo "✓ OK" || echo "✗ FAILED"
	@echo -n "Screenshot Service (8004): "
	@curl -sf http://localhost:8004/health > /dev/null && echo "✓ OK" || echo "✗ FAILED"
	@echo -n "Owner Extractor (8005): "
	@curl -sf http://localhost:8005/health > /dev/null && echo "✓ OK" || echo "✗ FAILED"
	@echo -n "Address Verifier (8006): "
	@curl -sf http://localhost:8006/health > /dev/null && echo "✓ OK" || echo "✗ FAILED"

# Testing
test:
	@echo "Running Python tests..."
	cd rise_pipeline && python -m pytest test_pipeline.py test_integrations.py -v
	@echo "✓ Tests complete"

test-services: up
	@echo "Testing service endpoints..."
	@echo "Testing TDLR Scraper..."
	@curl -sf -X POST http://localhost:8001/lookup -H "Content-Type: application/json" -d '{"business_name": "Test Electric", "city": "Austin"}' > /dev/null && echo "✓ TDLR OK" || echo "✗ TDLR FAILED"
	@echo "Testing BBB Scraper..."
	@curl -sf -X POST http://localhost:8002/lookup -H "Content-Type: application/json" -d '{"business_name": "Test Business", "city": "Austin", "state": "TX"}' > /dev/null && echo "✓ BBB OK" || echo "✗ BBB FAILED"
	@echo "Testing PageSpeed..."
	@curl -sf -X POST http://localhost:8003/analyze -H "Content-Type: application/json" -d '{"url": "https://example.com"}' > /dev/null && echo "✓ PageSpeed OK" || echo "✗ PageSpeed FAILED"

# Pipeline operations
prequalify:
	@echo "Running pre-qualification batch..."
	python run_prequalification_batch.py --limit 10

prequalify-all:
	@echo "Running pre-qualification for all leads..."
	python run_prequalification_batch.py --all

phase2:
	@echo "Running Phase 2 batch..."
	python run_phase_2_batch.py --limit 10

phase2-all:
	@echo "Running Phase 2 for all leads..."
	python run_phase_2_batch.py --all

# Dashboard
dashboard:
	@echo "Starting dashboard on http://localhost:8080"
	@command -v python3 >/dev/null 2>&1 && python3 -m http.server 8080 --directory dashboard || python -m http.server 8080 --directory dashboard

# Cleanup
clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleanup complete"

clean-all: clean down
	@echo "Removing Docker volumes..."
	cd custom_tools && docker compose down -v
	@echo "✓ Full cleanup complete"

# Quick start for new users
quickstart:
	@echo "🚀 Quick Start - Rise Local Lead Creation Pipeline"
	@echo "=================================================="
	@echo ""
	@echo "Step 1: Installing dependencies..."
	@make install
	@echo ""
	@echo "Step 2: Building Docker services..."
	@make build
	@echo ""
	@echo "Step 3: Starting services..."
	@make up
	@echo ""
	@echo "✅ Setup complete! Next steps:"
	@echo "  1. Configure your .env file with API keys"
	@echo "  2. Run 'make prequalify' to process leads"
	@echo "  3. Run 'make dashboard' to view the dashboard"
	@echo ""
