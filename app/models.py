"""Database models for Rick and Morty characters."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field


Base = declarative_base()


class Character(Base):
    """Database model for Rick and Morty characters."""
    
    __tablename__ = "characters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    species = Column(String(100), nullable=False, index=True)
    type = Column(String(100), nullable=True)
    gender = Column(String(50), nullable=True)
    origin_name = Column(String(255), nullable=True, index=True)
    origin_url = Column(String(500), nullable=True)
    location_name = Column(String(255), nullable=True)
    location_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    episode_urls = Column(Text, nullable=True)  # JSON string of episode URLs
    api_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Character(id={self.id}, name='{self.name}', species='{self.species}')>"


# Pydantic models for API responses
class CharacterOrigin(BaseModel):
    """Character origin information."""
    name: str
    url: str


class CharacterLocation(BaseModel):
    """Character location information."""
    name: str
    url: str


class CharacterResponse(BaseModel):
    """API response model for character data."""
    id: int
    name: str
    status: str
    species: str
    type: str = ""
    gender: str
    origin: CharacterOrigin
    location: CharacterLocation
    image: str
    episode: list[str]
    url: str
    created: datetime
    
    model_config = {"from_attributes": True}


class CharacterListResponse(BaseModel):
    """API response model for character list."""
    characters: list[CharacterResponse]
    total: int
    page: int = 1
    per_page: int = 20
    
    
class FilteredCharacterResponse(BaseModel):
    """Filtered character response for our API."""
    id: int
    name: str
    status: str
    species: str
    origin_name: str
    image_url: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")
    checks: dict = Field(..., description="Individual service checks")
    
    
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(..., description="Error timestamp")
