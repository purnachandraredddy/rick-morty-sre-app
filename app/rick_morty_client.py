"""Rick and Morty API client with retry logic and circuit breaker."""
import asyncio
import logging
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
import structlog
from circuitbreaker import circuit
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.models import CharacterResponse

logger = structlog.get_logger()


class RickMortyAPIError(Exception):
    """Custom exception for Rick and Morty API errors."""

    pass


class RickMortyClient:
    """Client for Rick and Morty API with resilience patterns."""

    def __init__(self):
        self.base_url = settings.rick_morty_api_url
        self.timeout = settings.rick_morty_timeout
        self.max_retries = settings.rick_morty_max_retries
        self.backoff_factor = settings.rick_morty_backoff_factor

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            headers={
                "User-Agent": f"{settings.app_name}/{settings.app_version}",
                "Accept": "application/json",
            },
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    @circuit(failure_threshold=5, recovery_timeout=30)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request with retry logic and circuit breaker."""
        # Ensure base_url ends with / and endpoint doesn't start with /
        base = self.base_url.rstrip("/") + "/"
        endpoint = endpoint.lstrip("/")
        url = urljoin(base, endpoint)

        try:
            logger.info("Making API request", url=url, params=params)
            response = await self.client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(
                "API request successful", url=url, status_code=response.status_code
            )
            return data

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error from Rick and Morty API",
                status_code=e.response.status_code,
                url=url,
                error=str(e),
            )
            if e.response.status_code == 429:
                # Rate limited - wait longer
                await asyncio.sleep(60)
            raise RickMortyAPIError(f"HTTP {e.response.status_code}: {str(e)}")

        except httpx.RequestError as e:
            logger.error("Request error to Rick and Morty API", url=url, error=str(e))
            raise RickMortyAPIError(f"Request failed: {str(e)}")

    async def get_character(self, character_id: int) -> Optional[CharacterResponse]:
        """Get a single character by ID."""
        try:
            data = await self._make_request(f"character/{character_id}")
            return CharacterResponse(**data)
        except RickMortyAPIError as e:
            logger.warning(
                "Failed to get character", character_id=character_id, error=str(e)
            )
            return None

    async def get_characters(
        self,
        page: int = 1,
        name: Optional[str] = None,
        status: Optional[str] = None,
        species: Optional[str] = None,
        gender: Optional[str] = None,
    ) -> Dict:
        """Get characters with optional filters."""
        params: Dict[str, str | int] = {"page": page}

        if name:
            params["name"] = name
        if status:
            params["status"] = status
        if species:
            params["species"] = species
        if gender:
            params["gender"] = gender

        return await self._make_request("character", params)

    async def get_all_filtered_characters(self) -> List[CharacterResponse]:
        """
        Get all characters matching our criteria:
        - Species: Human
        - Status: Alive
        - Origin: Earth (any variant)
        """
        all_characters: List[CharacterResponse] = []
        page = 1

        logger.info("Starting to fetch filtered characters")

        while True:
            try:
                data = await self.get_characters(
                    page=page, species="Human", status="Alive"
                )

                characters = data.get("results", [])
                if not characters:
                    break

                earth_characters = self._filter_earth_characters(characters)
                all_characters.extend(earth_characters)
                logger.info(
                    "Processed page",
                    page=page,
                    found_characters=len(earth_characters),
                    total_characters=len(all_characters),
                )

                next_page_num = self._extract_next_page_number(data, current_page=page)
                if not next_page_num:
                    break
                page = next_page_num

                # Rate limiting - be nice to the API
                await asyncio.sleep(0.1)

            except RickMortyAPIError as e:
                logger.error("Error fetching characters", page=page, error=str(e))
                break
            except Exception as e:
                logger.error(
                    "Unexpected error fetching characters", page=page, error=str(e)
                )
                break

        logger.info(
            "Finished fetching filtered characters", total_count=len(all_characters)
        )
        return all_characters

    def _filter_earth_characters(self, characters: List[Dict]) -> List[CharacterResponse]:
        """Return only characters whose origin name contains 'earth'."""
        filtered: List[CharacterResponse] = []
        for char_data in characters:
            origin_name = char_data.get("origin", {}).get("name", "").lower()
            if "earth" in origin_name:
                try:
                    filtered.append(CharacterResponse(**char_data))
                except Exception as e:
                    logger.warning(
                        "Failed to parse character data",
                        character_id=char_data.get("id"),
                        error=str(e),
                    )
        return filtered

    def _extract_next_page_number(self, data: Dict, current_page: int) -> Optional[int]:
        """Extract next page number from API response, if available and greater than current."""
        next_link = data.get("info", {}).get("next")
        if not next_link:
            return None
        parsed_url = urlparse(next_link)
        query_params = parse_qs(parsed_url.query)
        try:
            next_page_num = int(query_params.get("page", [0])[0])
        except (ValueError, TypeError):
            return None
        if next_page_num <= current_page:
            return None
        return next_page_num

    async def health_check(self) -> Dict:
        """Check API health."""
        try:
            # Simple health check by getting character count
            data = await self._make_request("character")
            info = data.get("info", {})

            return {
                "status": "healthy",
                "total_characters": info.get("count", 0),
                "pages": info.get("pages", 0),
                "api_url": self.base_url,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_url": self.base_url,
            }


# Global client instance
rick_morty_client = RickMortyClient()
