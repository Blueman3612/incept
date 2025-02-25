from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class QuestionDifficulty(str, Enum):
    """Enumeration for question difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionType(str, Enum):
    """Enumeration for question types."""
    MCQ = "multiple_choice"
    FRQ = "free_response"


class GradingCriterion(str, Enum):
    """Enumeration for grading criteria."""
    COMPLETENESS = "completeness"
    ANSWER_QUALITY = "answer_quality"
    EXPLANATION_QUALITY = "explanation_quality"
    LANGUAGE_QUALITY = "language_quality"
    STANDARD_ALIGNMENT = "standard_alignment"


class QuestionGradeRequest(BaseModel):
    """Model for question grading request."""
    question: str = Field(..., min_length=10, description="The question content to grade")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Optional metadata about the question")


class QuestionGradeResponse(BaseModel):
    """Model for question grading response."""
    passed: bool = Field(..., description="Whether the question passes quality standards")
    overall_score: float = Field(..., ge=0, le=1, description="Overall quality score (0-1)")
    criterion_scores: Dict[str, float] = Field(
        ..., description="Individual scores for each criterion"
    )
    failed_criteria: List[str] = Field(
        default_factory=list, description="List of criteria that failed to meet standards"
    )
    feedback: str = Field(..., description="Detailed feedback on the question quality")
    improvement_suggestions: Optional[Dict[str, List[str]]] = Field(
        default_factory=dict, description="Specific suggestions for improvement by criterion"
    )


class QuestionTagRequest(BaseModel):
    """Model for question tagging request."""
    question: str = Field(..., min_length=10, description="The question content to tag")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Optional metadata about the question")


class QuestionTagResponse(BaseModel):
    """Model for question tagging response."""
    subject: str = Field(..., description="Subject of the question")
    grade_level: int = Field(..., ge=1, le=8, description="Grade level (1-8)")
    standard: str = Field(..., description="Educational standard (e.g., CCSS code)")
    lesson: str = Field(..., description="Specific lesson within the standard")
    difficulty: QuestionDifficulty = Field(..., description="Difficulty level")
    question_type: QuestionType = Field(..., description="Type of question")
    tags: List[str] = Field(default_factory=list, description="Additional tags")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level in the tagging (0-1)")


class QuestionGenerateRequest(BaseModel):
    """Model for question generation request."""
    lesson: str = Field(..., description="Lesson to generate a question for")
    standard: Optional[str] = Field(None, description="Educational standard")
    difficulty: QuestionDifficulty = Field(..., description="Difficulty level")
    question_type: QuestionType = Field(default=QuestionType.MCQ, description="Type of question")
    example_question: Optional[str] = Field(None, description="Example question to base the new one on")
    additional_instructions: Optional[str] = Field(None, description="Additional instructions for generation")


class QuestionGenerateResponse(BaseModel):
    """Model for question generation response."""
    question: str = Field(..., description="The generated question")
    tags: Dict = Field(..., description="Tags for the generated question")
    quality_score: float = Field(..., ge=0, le=1, description="Quality score of the generated question") 