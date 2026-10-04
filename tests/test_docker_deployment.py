"""
Unit & Integration Tests for Production Docker Deployment Architecture

Tests:
- Dockerfile & Dockerfile.frontend multi-stage build structure & health check directives
- docker-compose.yml service declarations (FastAPI, Streamlit, Redis, PostgreSQL)
- Health check configurations & service dependencies
- Volume mounts & network isolation
"""

import pytest
import os
import re


def test_dockerfile_backend_structure():
    """Tests Dockerfile for multi-stage build, health check, and non-root security."""
    dockerfile_path = "Dockerfile"
    assert os.path.exists(dockerfile_path)

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "FROM python:3.11-slim as builder" in content
    assert "FROM python:3.11-slim as runner" in content
    assert "HEALTHCHECK" in content
    assert "useradd" in content or "USER appuser" in content
    assert "EXPOSE 8000" in content


def test_dockerfile_frontend_structure():
    """Tests Dockerfile.frontend for multi-stage build, health check, and non-root security."""
    dockerfile_path = "deployment/Dockerfile.frontend"
    assert os.path.exists(dockerfile_path)

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "FROM python:3.11-slim as builder" in content
    assert "FROM python:3.11-slim as runner" in content
    assert "HEALTHCHECK" in content
    assert "useradd" in content or "USER appuser" in content
    assert "EXPOSE 8501" in content


def test_docker_compose_configuration():
    """Tests docker-compose.yml for 4 services, health checks, volumes, and networks."""
    compose_path = "docker-compose.yml"
    assert os.path.exists(compose_path)

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify all 4 microservices
    assert "database:" in content
    assert "redis:" in content
    assert "backend:" in content
    assert "frontend:" in content

    # Verify persistent volumes & network
    assert "postgres_data:" in content
    assert "redis_data:" in content
    assert "emergency_net:" in content

    # Verify healthchecks for all services
    assert "healthcheck:" in content
    assert "pg_isready" in content
    assert "redis-cli" in content
    assert "condition: service_healthy" in content


def test_env_files_exist():
    """Tests that .env.example exists with required variables."""
    assert os.path.exists(".env.example")

    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read()

    assert "POSTGRES_DB" in content
    assert "REDIS_URL" in content
    assert "SECRET_KEY" in content
    assert "GEMINI_API_KEY" in content
