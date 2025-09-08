"""Integration tests for API endpoints."""
import pytest
from httpx import AsyncClient

from app.models import Character


class TestHealthCheckEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_healthcheck_endpoint(self, client: AsyncClient):
        """Test health check endpoint returns correct structure."""
        response = await client.get("/healthcheck")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    @pytest.mark.asyncio
    async def test_healthcheck_rate_limit(self, client: AsyncClient):
        """Test health check rate limiting."""
        # Make multiple requests quickly
        responses = []
        for _ in range(12):  # Exceed 10/minute limit
            response = await client.get("/healthcheck")
            responses.append(response.status_code)

        # Should get some 429 responses
        assert 429 in responses


class TestCharactersEndpoint:
    """Test characters endpoint."""

    @pytest.mark.asyncio
    async def test_get_characters_empty(self, client: AsyncClient):
        """Test getting characters when database is empty."""
        response = await client.get("/characters")

        assert response.status_code == 200
        data = response.json()

        assert "characters" in data
        assert "pagination" in data
        assert data["characters"] == []
        assert data["pagination"]["total"] == 0

    @pytest.mark.asyncio
    async def test_get_characters_with_data(
        self, client: AsyncClient, db_session, sample_character_data
    ):
        """Test getting characters with data."""
        # Add test character
        character = Character(**sample_character_data)
        db_session.add(character)
        await db_session.commit()

        response = await client.get("/characters")

        assert response.status_code == 200
        data = response.json()

        assert len(data["characters"]) == 1
        assert data["pagination"]["total"] == 1
        assert data["characters"][0]["id"] == 1
        assert data["characters"][0]["name"] == "Rick Sanchez"

    @pytest.mark.asyncio
    async def test_get_characters_pagination(self, client: AsyncClient, db_session):
        """Test character pagination."""
        # Add multiple test characters
        for i in range(5):
            character = Character(
                id=i + 1,
                name=f"Character {i + 1}",
                status="Alive",
                species="Human",
                origin_name="Earth",
                image_url="https://example.com/image.jpg",
            )
            db_session.add(character)
        await db_session.commit()

        # Test pagination
        response = await client.get("/characters?page=2&per_page=2")

        assert response.status_code == 200
        data = response.json()

        assert len(data["characters"]) == 2
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 2
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["total_pages"] == 3
        assert data["pagination"]["has_prev"] is True
        assert data["pagination"]["has_next"] is True

    @pytest.mark.asyncio
    async def test_get_characters_sorting(self, client: AsyncClient, db_session):
        """Test character sorting."""
        # Add test characters
        names = ["Charlie", "Alice", "Bob"]
        for i, name in enumerate(names):
            character = Character(
                id=i + 1,
                name=name,
                status="Alive",
                species="Human",
                origin_name="Earth",
                image_url="https://example.com/image.jpg",
            )
            db_session.add(character)
        await db_session.commit()

        # Test ascending sort
        response = await client.get("/characters?sort=name&order=asc")

        assert response.status_code == 200
        data = response.json()

        names_result = [char["name"] for char in data["characters"]]
        assert names_result == ["Alice", "Bob", "Charlie"]

        # Test descending sort
        response = await client.get("/characters?sort=name&order=desc")

        assert response.status_code == 200
        data = response.json()

        names_result = [char["name"] for char in data["characters"]]
        assert names_result == ["Charlie", "Bob", "Alice"]

    @pytest.mark.asyncio
    async def test_get_characters_invalid_params(self, client: AsyncClient):
        """Test invalid parameters for characters endpoint."""
        # Invalid page
        response = await client.get("/characters?page=0")
        assert response.status_code == 400

        # Invalid per_page
        response = await client.get("/characters?per_page=0")
        assert response.status_code == 400

        response = await client.get("/characters?per_page=101")
        assert response.status_code == 400

        # Invalid sort field
        response = await client.get("/characters?sort=invalid")
        assert response.status_code == 400

        # Invalid order
        response = await client.get("/characters?order=invalid")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_character_by_id(
        self, client: AsyncClient, db_session, sample_character_data
    ):
        """Test getting character by ID."""
        # Add test character
        character = Character(**sample_character_data)
        db_session.add(character)
        await db_session.commit()

        response = await client.get("/characters/1")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 1
        assert data["name"] == "Rick Sanchez"
        assert data["status"] == "Alive"
        assert data["species"] == "Human"

    @pytest.mark.asyncio
    async def test_get_character_by_id_not_found(self, client: AsyncClient):
        """Test getting non-existent character."""
        response = await client.get("/characters/999")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Character not found"

    @pytest.mark.asyncio
    async def test_get_character_by_id_invalid(self, client: AsyncClient):
        """Test getting character with invalid ID."""
        response = await client.get("/characters/0")

        assert response.status_code == 400
        data = response.json()
        assert "Character ID must be >= 1" in data["detail"]


class TestStatsEndpoint:
    """Test stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, client: AsyncClient):
        """Test getting stats with empty database."""
        response = await client.get("/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_characters" in data
        assert "species_breakdown" in data
        assert "status_breakdown" in data
        assert "last_sync" in data
        assert data["total_characters"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, client: AsyncClient, db_session):
        """Test getting stats with data."""
        # Add test characters
        characters_data = [
            {
                "id": 1,
                "name": "Rick",
                "status": "Alive",
                "species": "Human",
                "origin_name": "Earth",
            },
            {
                "id": 2,
                "name": "Morty",
                "status": "Alive",
                "species": "Human",
                "origin_name": "Earth",
            },
            {
                "id": 3,
                "name": "Alien",
                "status": "Dead",
                "species": "Alien",
                "origin_name": "Mars",
            },
        ]

        for char_data in characters_data:
            char_data["image_url"] = "https://example.com/image.jpg"
            character = Character(**char_data)
            db_session.add(character)
        await db_session.commit()

        response = await client.get("/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["total_characters"] == 3
        assert data["species_breakdown"]["Human"] == 2
        assert data["species_breakdown"]["Alien"] == 1
        assert data["status_breakdown"]["Alive"] == 2
        assert data["status_breakdown"]["Dead"] == 1


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client: AsyncClient):
        """Test metrics endpoint returns Prometheus format."""
        response = await client.get("/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

        content = response.text
        assert "# HELP" in content or "# TYPE" in content


class TestSyncEndpoint:
    """Test sync endpoint."""

    @pytest.mark.asyncio
    async def test_sync_endpoint(self, client: AsyncClient):
        """Test manual sync endpoint."""
        response = await client.post("/sync")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "status" in data
        assert data["status"] == "in_progress"


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_404_endpoint(self, client: AsyncClient):
        """Test 404 error handling."""
        response = await client.get("/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, client: AsyncClient):
        """Test method not allowed."""
        response = await client.post("/characters")

        assert response.status_code == 405
