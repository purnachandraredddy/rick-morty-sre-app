"""Business logic services."""
import json
from datetime import datetime
from typing import List, Optional

import structlog
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache
from app.models import Character, FilteredCharacterResponse
from app.rick_morty_client import rick_morty_client

logger = structlog.get_logger()


class CharacterService:
    """Service for managing character data."""

    @staticmethod
    async def sync_characters_from_api(db: AsyncSession) -> int:
        """Sync characters from Rick and Morty API to database."""
        logger.info("Starting character sync from API")

        try:
            # Get filtered characters from API
            api_characters = await rick_morty_client.get_all_filtered_characters()

            if not api_characters:
                logger.warning("No characters received from API")
                return 0

            # Convert to database models and upsert
            synced_count = 0
            for api_char in api_characters:
                try:
                    # Check if character already exists
                    result = await db.execute(
                        select(Character).where(Character.id == api_char.id)
                    )
                    existing_char = result.scalar_one_or_none()

                    if existing_char:
                        # Update existing character
                        existing_char.name = api_char.name
                        existing_char.status = api_char.status
                        existing_char.species = api_char.species
                        existing_char.type = api_char.type
                        existing_char.gender = api_char.gender
                        existing_char.origin_name = api_char.origin.name
                        existing_char.origin_url = api_char.origin.url
                        existing_char.location_name = api_char.location.name
                        existing_char.location_url = api_char.location.url
                        existing_char.image_url = api_char.image
                        existing_char.episode_urls = json.dumps(api_char.episode)
                        existing_char.api_url = api_char.url
                        existing_char.updated_at = datetime.utcnow()
                    else:
                        # Create new character
                        new_char = Character(
                            id=api_char.id,
                            name=api_char.name,
                            status=api_char.status,
                            species=api_char.species,
                            type=api_char.type,
                            gender=api_char.gender,
                            origin_name=api_char.origin.name,
                            origin_url=api_char.origin.url,
                            location_name=api_char.location.name,
                            location_url=api_char.location.url,
                            image_url=api_char.image,
                            episode_urls=json.dumps(api_char.episode),
                            api_url=api_char.url,
                        )
                        db.add(new_char)

                    synced_count += 1

                except Exception as e:
                    logger.error(
                        "Failed to sync character",
                        character_id=api_char.id,
                        character_name=api_char.name,
                        error=str(e),
                    )
                    continue

            await db.commit()

            # Clear cache after sync
            await cache.clear_pattern("characters:*")

            logger.info("Character sync completed", synced_count=synced_count)
            return synced_count

        except Exception as e:
            logger.error("Character sync failed", error=str(e))
            await db.rollback()
            raise

    @staticmethod
    async def get_characters(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "id",
        sort_order: str = "asc",
    ) -> tuple[List[FilteredCharacterResponse], int]:
        """Get paginated characters from database."""

        # Check cache first
        cache_key = (
            f"characters:page:{page}:per_page:{per_page}:sort:{sort_by}:{sort_order}"
        )
        cached_result = await cache.get(cache_key)

        if cached_result:
            logger.info("Returning cached characters", page=page, per_page=per_page)
            characters_data, total = cached_result
            characters = [FilteredCharacterResponse(**char) for char in characters_data]
            return characters, total

        try:
            # Build query
            query = select(Character)

            # Add sorting
            if sort_by == "name":
                order_column = Character.name
            elif sort_by == "created_at":
                order_column = Character.created_at
            else:
                order_column = Character.id

            if sort_order.lower() == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))

            # Add pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

            # Execute query
            result = await db.execute(query)
            characters = result.scalars().all()

            # Get total count
            count_query = select(func.count(Character.id))
            count_result = await db.execute(count_query)
            total = count_result.scalar()

            # Convert to response models
            character_responses = []
            for char in characters:
                response = FilteredCharacterResponse(
                    id=char.id,
                    name=char.name,
                    status=char.status,
                    species=char.species,
                    origin_name=char.origin_name or "",
                    image_url=char.image_url or "",
                    created_at=char.created_at,
                )
                character_responses.append(response)

            # Cache the result
            cache_data = ([char.model_dump() for char in character_responses], total)
            await cache.set(cache_key, cache_data, ttl=300)  # Cache for 5 minutes

            logger.info(
                "Retrieved characters from database",
                page=page,
                per_page=per_page,
                count=len(character_responses),
                total=total,
            )

            return character_responses, total

        except Exception as e:
            logger.error("Failed to get characters", error=str(e))
            raise

    @staticmethod
    async def get_character_by_id(
        db: AsyncSession, character_id: int
    ) -> Optional[FilteredCharacterResponse]:
        """Get a single character by ID."""

        # Check cache first
        cache_key = f"character:{character_id}"
        cached_char = await cache.get(cache_key)

        if cached_char:
            logger.info("Returning cached character", character_id=character_id)
            return FilteredCharacterResponse(**cached_char)

        try:
            result = await db.execute(
                select(Character).where(Character.id == character_id)
            )
            character = result.scalar_one_or_none()

            if not character:
                return None

            response = FilteredCharacterResponse(
                id=character.id,
                name=character.name,
                status=character.status,
                species=character.species,
                origin_name=character.origin_name or "",
                image_url=character.image_url or "",
                created_at=character.created_at,
            )

            # Cache the result
            await cache.set(
                cache_key, response.model_dump(), ttl=3600
            )  # Cache for 1 hour

            logger.info("Retrieved character by ID", character_id=character_id)
            return response

        except Exception as e:
            logger.error(
                "Failed to get character by ID", character_id=character_id, error=str(e)
            )
            raise

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        """Get character statistics."""

        cache_key = "character_stats"
        cached_stats = await cache.get(cache_key)

        if cached_stats:
            logger.info("Returning cached character stats")
            return cached_stats

        try:
            # Total count
            total_query = select(func.count(Character.id))
            total_result = await db.execute(total_query)
            total_count = total_result.scalar()

            # Count by species
            species_query = select(
                Character.species, func.count(Character.id)
            ).group_by(Character.species)
            species_result = await db.execute(species_query)
            species_counts = dict(species_result.all())

            # Count by status
            status_query = select(Character.status, func.count(Character.id)).group_by(
                Character.status
            )
            status_result = await db.execute(status_query)
            status_counts = dict(status_result.all())

            # Most recent sync
            latest_query = select(func.max(Character.updated_at))
            latest_result = await db.execute(latest_query)
            last_sync = latest_result.scalar()

            stats = {
                "total_characters": total_count,
                "species_breakdown": species_counts,
                "status_breakdown": status_counts,
                "last_sync": last_sync.isoformat() if last_sync else None,
            }

            # Cache stats for 10 minutes
            await cache.set(cache_key, stats, ttl=600)

            logger.info("Generated character stats", total_characters=total_count)
            return stats

        except Exception as e:
            logger.error("Failed to get character stats", error=str(e))
            raise


# Global service instance
character_service = CharacterService()
