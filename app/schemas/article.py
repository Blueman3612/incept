from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    """Enumeration for article difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


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
    difficulty_level: DifficultyLevel
    key_concepts: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)


class ArticleResponse(ArticleInDB):
    """Model for article response."""
    pass


class ArticleGenerateRequest(BaseModel):
    """Model for article generation request."""
    course: str = Field(..., min_length=2, max_length=50, description="Course name (e.g., Language, Math, Science)")
    grade_level: int = Field(..., ge=1, le=8, description="Target grade level (1-8)")
    lesson: str = Field(..., min_length=3, max_length=200, description="The lesson topic (e.g., main_idea, supporting_details)")
    lesson_description: Optional[str] = Field(None, min_length=5, max_length=500, description="Optional detailed description of the lesson objectives")
    keywords: Optional[List[str]] = Field(default_factory=list, description="Key terms or concepts to include")


class ArticleGradeRequest(BaseModel):
    """Model for article grading request."""
    content: str = Field(..., min_length=50, description="The article content to evaluate")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata about the article")


class ArticleGradeResponse(BaseModel):
    """Model for article grading response."""
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score (0.0-1.0)")
    criterion_scores: Dict[str, float] = Field(..., description="Scores for each quality criterion")
    criterion_feedback: Dict[str, str] = Field(..., description="Detailed feedback for each criterion")
    critical_issues: List[str] = Field(default_factory=list, description="List of critical issues identified")
    passing: bool = Field(..., description="Whether the article passes quality standards")
    feedback: str = Field(..., description="Comprehensive feedback with improvement suggestions")
    timestamp: str = Field(..., description="Timestamp of the evaluation") 