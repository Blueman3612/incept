from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel
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

# Add the scripts directory to the path so we can import from generate_questions.py
scripts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "scripts")
sys.path.append(scripts_path)

from scripts.generate_questions import generate_question_for_api

router = APIRouter(prefix="/questions", tags=["questions"])


async def get_question_service() -> QuestionService:
    """Dependency to get QuestionService instance."""
    return QuestionService()


@router.post("/grade", response_model=QuestionGradeResponse, status_code=200)
async def grade_question(
    request: QuestionGradeRequest,
    question_service: QuestionService = Depends(get_question_service)
) -> QuestionGradeResponse:
    """
    Grade a question against quality criteria for educational content.
    
    The grading is based on analyzing hundreds of good examples from our test database.
    Each question is evaluated on multiple criteria including completeness, answer quality,
    explanation quality, and language quality.
    
    Args:
        request: Question content to grade and optional metadata
        question_service: Service for question operations (injected)
        
    Returns:
        QuestionGradeResponse: Detailed grading information including overall pass/fail,
        scores per criterion, and specific improvement suggestions
        
    Raises:
        HTTPException: If question grading fails
    """
    try:
        result = await question_service.grade_question(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to grade question: {str(e)}"
        )


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