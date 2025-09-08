"""Unit tests for data models."""
from datetime import datetime

import pytest

from app.models import Character, FilteredCharacterResponse, HealthCheckResponse


class TestCharacter:
    """Test Character database model."""

    def test_character_creation(self, sample_character_data):
        """Test character model creation."""
        character = Character(**sample_character_data)

        assert character.id == 1
        assert character.name == "Rick Sanchez"
        assert character.status == "Alive"
        assert character.species == "Human"
        assert character.origin_name == "Earth (C-137)"

    def test_character_repr(self, sample_character_data):
        """Test character string representation."""
        character = Character(**sample_character_data)
        repr_str = repr(character)

        assert "Character(id=1" in repr_str
        assert "name='Rick Sanchez'" in repr_str
        assert "species='Human'" in repr_str


class TestFilteredCharacterResponse:
    """Test FilteredCharacterResponse model."""

    def test_filtered_character_response(self):
        """Test filtered character response creation."""
        data = {
            "id": 1,
            "name": "Rick Sanchez",
            "status": "Alive",
            "species": "Human",
            "origin_name": "Earth (C-137)",
            "image_url": "https://example.com/image.jpg",
            "created_at": datetime.utcnow(),
        }

        response = FilteredCharacterResponse(**data)

        assert response.id == 1
        assert response.name == "Rick Sanchez"
        assert response.status == "Alive"
        assert response.species == "Human"
        assert response.origin_name == "Earth (C-137)"

    def test_filtered_character_response_dict(self):
        """Test converting filtered character response to dict."""
        data = {
            "id": 1,
            "name": "Rick Sanchez",
            "status": "Alive",
            "species": "Human",
            "origin_name": "Earth (C-137)",
            "image_url": "https://example.com/image.jpg",
            "created_at": datetime.utcnow(),
        }

        response = FilteredCharacterResponse(**data)
        result_dict = response.model_dump()

        assert result_dict["id"] == 1
        assert result_dict["name"] == "Rick Sanchez"
        assert "created_at" in result_dict


class TestHealthCheckResponse:
    """Test HealthCheckResponse model."""

    def test_health_check_response(self):
        """Test health check response creation."""
        data = {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "version": "1.0.0",
            "checks": {
                "database": {"status": "healthy"},
                "cache": {"status": "healthy"},
            },
        }

        response = HealthCheckResponse(**data)

        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert "database" in response.checks
        assert "cache" in response.checks

    def test_health_check_response_unhealthy(self):
        """Test unhealthy health check response."""
        data = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow(),
            "version": "1.0.0",
            "checks": {
                "database": {"status": "unhealthy", "error": "Connection failed"},
            },
        }

        response = HealthCheckResponse(**data)

        assert response.status == "unhealthy"
        assert response.checks["database"]["status"] == "unhealthy"
        assert "error" in response.checks["database"]
