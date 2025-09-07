"""Unit tests for services."""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.services import CharacterService
from app.models import Character, FilteredCharacterResponse


class TestCharacterService:
    """Test CharacterService."""
    
    @pytest.mark.asyncio
    async def test_get_characters_empty_db(self, db_session):
        """Test getting characters from empty database."""
        characters, total = await CharacterService.get_characters(db_session)
        
        assert characters == []
        assert total == 0
    
    @pytest.mark.asyncio
    async def test_get_characters_with_data(self, db_session, sample_character_data):
        """Test getting characters with data in database."""
        # Add a character to the database
        character = Character(**sample_character_data)
        db_session.add(character)
        await db_session.commit()
        
        characters, total = await CharacterService.get_characters(db_session)
        
        assert len(characters) == 1
        assert total == 1
        assert characters[0].id == 1
        assert characters[0].name == "Rick Sanchez"
    
    @pytest.mark.asyncio
    async def test_get_characters_pagination(self, db_session):
        """Test character pagination."""
        # Add multiple characters
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
        characters, total = await CharacterService.get_characters(
            db_session, page=2, per_page=2
        )
        
        assert len(characters) == 2
        assert total == 5
        assert characters[0].id == 3
        assert characters[1].id == 4
    
    @pytest.mark.asyncio
    async def test_get_characters_sorting(self, db_session):
        """Test character sorting."""
        # Add characters in random order
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
        
        # Test sorting by name ascending
        characters, total = await CharacterService.get_characters(
            db_session, sort_by="name", sort_order="asc"
        )
        
        assert len(characters) == 3
        assert characters[0].name == "Alice"
        assert characters[1].name == "Bob"
        assert characters[2].name == "Charlie"
        
        # Test sorting by name descending
        characters, total = await CharacterService.get_characters(
            db_session, sort_by="name", sort_order="desc"
        )
        
        assert characters[0].name == "Charlie"
        assert characters[1].name == "Bob"
        assert characters[2].name == "Alice"
    
    @pytest.mark.asyncio
    async def test_get_character_by_id(self, db_session, sample_character_data):
        """Test getting character by ID."""
        # Add a character to the database
        character = Character(**sample_character_data)
        db_session.add(character)
        await db_session.commit()
        
        # Test getting existing character
        result = await CharacterService.get_character_by_id(db_session, 1)
        
        assert result is not None
        assert result.id == 1
        assert result.name == "Rick Sanchez"
        
        # Test getting non-existent character
        result = await CharacterService.get_character_by_id(db_session, 999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_stats(self, db_session):
        """Test getting character statistics."""
        # Add test characters
        characters_data = [
            {"id": 1, "name": "Rick", "status": "Alive", "species": "Human", "origin_name": "Earth"},
            {"id": 2, "name": "Morty", "status": "Alive", "species": "Human", "origin_name": "Earth"},
            {"id": 3, "name": "Alien", "status": "Dead", "species": "Alien", "origin_name": "Mars"},
        ]
        
        for char_data in characters_data:
            char_data["image_url"] = "https://example.com/image.jpg"
            character = Character(**char_data)
            db_session.add(character)
        await db_session.commit()
        
        stats = await CharacterService.get_stats(db_session)
        
        assert stats["total_characters"] == 3
        assert stats["species_breakdown"]["Human"] == 2
        assert stats["species_breakdown"]["Alien"] == 1
        assert stats["status_breakdown"]["Alive"] == 2
        assert stats["status_breakdown"]["Dead"] == 1
        assert "last_sync" in stats
    
    @pytest.mark.asyncio
    @patch('app.services.rick_morty_client.get_all_filtered_characters')
    async def test_sync_characters_from_api(self, mock_api_call, db_session):
        """Test syncing characters from API."""
        # Mock API response
        mock_character = AsyncMock()
        mock_character.id = 1
        mock_character.name = "Rick Sanchez"
        mock_character.status = "Alive"
        mock_character.species = "Human"
        mock_character.type = ""
        mock_character.gender = "Male"
        mock_character.origin.name = "Earth (C-137)"
        mock_character.origin.url = "https://rickandmortyapi.com/api/location/1"
        mock_character.location.name = "Citadel of Ricks"
        mock_character.location.url = "https://rickandmortyapi.com/api/location/3"
        mock_character.image = "https://rickandmortyapi.com/api/character/avatar/1.jpeg"
        mock_character.episode = ["https://rickandmortyapi.com/api/episode/1"]
        mock_character.url = "https://rickandmortyapi.com/api/character/1"
        
        mock_api_call.return_value = [mock_character]
        
        # Test sync
        synced_count = await CharacterService.sync_characters_from_api(db_session)
        
        assert synced_count == 1
        
        # Verify character was added to database
        characters, total = await CharacterService.get_characters(db_session)
        assert total == 1
        assert characters[0].id == 1
        assert characters[0].name == "Rick Sanchez"
    
    @pytest.mark.asyncio
    @patch('app.services.rick_morty_client.get_all_filtered_characters')
    async def test_sync_characters_update_existing(self, mock_api_call, db_session, sample_character_data):
        """Test updating existing characters during sync."""
        # Add existing character
        character = Character(**sample_character_data)
        db_session.add(character)
        await db_session.commit()
        
        # Mock API response with updated data
        mock_character = AsyncMock()
        mock_character.id = 1
        mock_character.name = "Rick Sanchez Updated"
        mock_character.status = "Alive"
        mock_character.species = "Human"
        mock_character.type = ""
        mock_character.gender = "Male"
        mock_character.origin.name = "Earth (C-137)"
        mock_character.origin.url = "https://rickandmortyapi.com/api/location/1"
        mock_character.location.name = "Citadel of Ricks"
        mock_character.location.url = "https://rickandmortyapi.com/api/location/3"
        mock_character.image = "https://rickandmortyapi.com/api/character/avatar/1.jpeg"
        mock_character.episode = ["https://rickandmortyapi.com/api/episode/1"]
        mock_character.url = "https://rickandmortyapi.com/api/character/1"
        
        mock_api_call.return_value = [mock_character]
        
        # Test sync
        synced_count = await CharacterService.sync_characters_from_api(db_session)
        
        assert synced_count == 1
        
        # Verify character was updated
        updated_character = await CharacterService.get_character_by_id(db_session, 1)
        assert updated_character.name == "Rick Sanchez Updated"
