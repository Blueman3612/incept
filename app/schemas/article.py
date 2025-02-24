from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ArticleBase(BaseModel):
    """Base article model with common attributes."""
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=50)
    grade_level: int = Field(..., ge=1, le=8)
    subject: str = Field(..., min_length=2, max_length=50)


class ArticleCreate(ArticleBase):
    """Model for creating a new article."""
    keywords: List[str] = Field(default_factory=list)
    target_age_range: List[int] = Field(..., min_items=2, max_items=2)


class ArticleInDB(ArticleBase):
    """Model for article as stored in database."""
    id: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = Field(default_factory=list)
    quality_score: Optional[float] = None
    readability_score: Optional[float] = None


class ArticleResponse(ArticleInDB):
    """Model for article response."""
    pass


class ArticleGenerateRequest(BaseModel):
    """Model for article generation request."""
    topic: str = Field(..., min_length=3, max_length=200)
    grade_level: int = Field(..., ge=1, le=8)
    subject: str = Field(..., min_length=2, max_length=50)
    length: str = Field(..., regex="^(short|medium|long)$")
    keywords: Optional[List[str]] = Field(default_factory=list)
    style: Optional[str] = Field(default="standard", regex="^(standard|creative|technical)$") 