from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.services.question_service import QuestionService
from app.schemas.question import (
    QuestionGradeRequest,
    QuestionGradeResponse,
    QuestionTagRequest,
    QuestionTagResponse,
    QuestionGenerateRequest,
    QuestionGenerateResponse,
    QuestionDifficulty
)
import sys
import os
from app.services.grader_service import grade_question

# Add the scripts directory to the path so we can import from generate_questions.py
scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "scripts")
sys.path.append(scripts_path)

from scripts.generate_questions import generate_question_for_api

router = APIRouter(prefix="/questions", tags=["questions"])


async def get_question_service() -> QuestionService:
    """Dependency to get QuestionService instance."""
    return QuestionService()


# Request/Response models for the API
class GradeQuestionRequest(BaseModel):
    """Request model for grading a question."""
    question: str = Field(..., description="The question content to evaluate")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata about the question")

class GradeQuestionResponse(BaseModel):
    """Response model for the question grading endpoint."""
    overall_result: str = Field(..., description="The overall result (pass/fail)")
    message: str = Field(..., description="A message summarizing the grading result")
    scores: Dict[str, float] = Field(..., description="Scores for each quality criterion")
    criteria_results: Dict[str, bool] = Field(..., description="Pass/fail result for each criterion")
    critical_issues: List[str] = Field(default_factory=list, description="List of critical issues that caused the content to fail")
    confidence: float = Field(..., description="Confidence score of the evaluation (0.0-1.0)")
    feedback: Dict[str, str] = Field(..., description="Detailed feedback for each criterion")

@router.post("/grade", response_model=GradeQuestionResponse)
async def grade_question_endpoint(request: GradeQuestionRequest):
    """
    Grade a question for quality based on predefined criteria.
    
    The grader evaluates the question on four key criteria:
    - Completeness: All required components are present
    - Answer Quality: Answers and distractors are well-designed
    - Explanation Quality: Explanations are clear and educational
    - Language Quality: Language is appropriate and grammatically correct
    
    The grader is extremely strict to ensure high precision. Critical issues will
    automatically cause a fail, regardless of the overall score. The system
    prioritizes precision over recall, meaning it may reject some good content
    to ensure no bad content is approved.
    
    Returns detailed scores, feedback, and any critical issues identified.
    """
    try:
        # Call the grader service
        result = grade_question(request.question, request.metadata)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to grade question: {str(e)}")


@router.post("/generate", response_model=QuestionGenerateResponse, status_code=200)
async def generate_question(request: QuestionGenerateRequest):
    """
    Generate a new educational question or a variation of an existing question.
    
    This endpoint creates a high-quality grade 4 language arts question based on:
    - Lesson topic (e.g., "main_idea", "supporting_details", "authors_purpose")
    - Difficulty level ("easy", "medium", "hard")
    
    If generating a variation, provide an example_question to base the new question on.
    The endpoint will attempt to generate a question that passes all quality criteria.
    If it can't generate a perfect question after multiple attempts, it returns the
    best result with detailed feedback.
    
    Returns the generated question content, quality assessment, and metadata.
    """
    try:
        result = await generate_question_for_api(
            lesson=request.lesson,
            difficulty=request.difficulty,
            example_question=request.example_question
        )
        
        # Validate that the result follows our schema
        return QuestionGenerateResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate question: {str(e)}")


# Placeholder for future tag endpoint if needed
@router.post("/tag")
async def tag_question():
    """
    Tag a question with subject, grade, standard, lesson, and difficulty.
    This endpoint is not yet implemented.
    """
    return {"message": "This endpoint is not yet implemented"}


# Additional endpoints will be implemented in the future:

# @router.post("/tag", response_model=QuestionTagResponse, status_code=200)
# async def tag_question(
#     request: QuestionTagRequest,
#     question_service: QuestionService = Depends(get_question_service)
# ) -> QuestionTagResponse:
#     """Tag a question with subject, grade, standard, lesson, and difficulty."""
#     pass


# @router.post("/generate", response_model=QuestionGenerateResponse, status_code=201)
# async def generate_question(
#     request: QuestionGenerateRequest,
#     question_service: QuestionService = Depends(get_question_service)
# ) -> QuestionGenerateResponse:
#     """Generate a question based on specified parameters or similar to an example."""
#     pass 