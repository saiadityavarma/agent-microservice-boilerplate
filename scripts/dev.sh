#!/bin/bash
# scripts/dev.sh - Development helper script

set -e

COMPOSE_FILE="docker/docker-compose.yml"

case "$1" in
  start)
    echo "Starting development environment..."
    docker compose -f $COMPOSE_FILE up -d --build
    echo ""
    echo "✓ API: http://localhost:8000"
    echo "✓ Docs: http://localhost:8000/docs"
    echo "✓ Health: http://localhost:8000/health/live"
    ;;

  stop)
    echo "Stopping development environment..."
    docker compose -f $COMPOSE_FILE down
    ;;

  logs)
    docker compose -f $COMPOSE_FILE logs -f api
    ;;

  shell)
    docker compose -f $COMPOSE_FILE exec api bash
    ;;

  test)
    echo "Running tests..."
    docker compose -f $COMPOSE_FILE exec api pytest tests/ -v
    ;;

  lint)
    echo "Running linter..."
    docker compose -f $COMPOSE_FILE exec api ruff check src/
    ;;

  format)
    echo "Formatting code..."
    docker compose -f $COMPOSE_FILE exec api ruff format src/
    ;;

  migrate)
    echo "Running migrations..."
    docker compose -f $COMPOSE_FILE exec api alembic upgrade head
    ;;

  reset)
    echo "Resetting environment..."
    docker compose -f $COMPOSE_FILE down -v
    docker compose -f $COMPOSE_FILE up -d --build
    ;;

  *)
    echo "Usage: $0 {start|stop|logs|shell|test|lint|format|migrate|reset}"
    exit 1
    ;;
esac
