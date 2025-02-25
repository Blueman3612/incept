from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict

from app.schemas.question import (
    QuestionGradeRequest,
    QuestionGradeResponse,
    QuestionTagRequest,
    QuestionTagResponse,
    QuestionGenerateRequest,
    QuestionGenerateResponse
)
from app.services.question_service import QuestionService

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