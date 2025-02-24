from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class QualityStatus(str, Enum):
    GOOD = "good"
    BAD = "bad"

class QualityCriterion(str, Enum):
    VOCABULARY = "vocabulary"
    QUESTION_STEM = "question_stem"
    DISTRACTORS = "distractors"
    CORRECT_ANSWER = "correct_answer"
    GRAMMAR = "grammar"
    STANDARD_ALIGNMENT = "standard_alignment"

class MutationType(str, Enum):
    ORIGINAL = "original"
    VOCABULARY_MUTATION = "vocabulary_mutation"
    STEM_MUTATION = "stem_mutation"
    DISTRACTOR_MUTATION = "distractor_mutation"
    ANSWER_MUTATION = "answer_mutation"
    GRAMMAR_MUTATION = "grammar_mutation"
    STANDARD_MUTATION = "standard_mutation"

class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class TestExample(BaseModel):
    """Model for storing test examples in the test harness"""
    id: Optional[str] = Field(None)
    content: str = Field(..., description="The actual question content")
    quality_status: QualityStatus = Field(..., description="Whether this is a good or bad example")
    quality_criterion: QualityCriterion = Field(..., description="The quality criterion being tested")
    mutation_type: MutationType = Field(..., description="Type of mutation if this is a bad example")
    lesson: str = Field(..., description="The lesson/topic this question belongs to")
    difficulty_level: DifficultyLevel = Field(..., description="Difficulty level of the question")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict, description="Additional metadata about the example")

    class Config:
        use_enum_values = True

class QualityMetrics(BaseModel):
    """Model for tracking quality control metrics"""
    total_examples: int = 0
    good_examples: int = 0
    bad_examples: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    metrics_by_criterion: dict = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class QualityCheckResult(BaseModel):
    """Model for quality check results"""
    passed: bool = False
    criterion_scores: dict = Field(default_factory=dict)
    failed_criteria: List[QualityCriterion] = Field(default_factory=list)
    feedback: str = ""
    metadata: dict = Field(default_factory=dict) 