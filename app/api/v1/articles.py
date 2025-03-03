from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.schemas.article import (
    ArticleGenerateRequest, 
    ArticleInDB, 
    ArticleResponse, 
    ArticleGradeRequest, 
    ArticleGradeResponse
)
from app.services.article_service import ArticleService
from app.services.article_grader import grade_article
from app.services.article_generator import generate_article_with_grading

router = APIRouter(prefix="/articles", tags=["articles"])


async def get_article_service() -> ArticleService:
    """Dependency to get ArticleService instance."""
    return ArticleService()


@router.post("/generate", response_model=ArticleResponse, status_code=201)
async def generate_article(
    request: ArticleGenerateRequest,
    article_service: ArticleService = Depends(get_article_service)
) -> ArticleResponse:
    """
    Generate an educational article based on the provided parameters.
    
    The article generator creates high-quality educational content following 
    Direct Instruction principles. The generator:
    
    1. Creates an initial article draft
    2. Evaluates it against strict quality criteria
    3. Makes targeted improvements based on quality feedback
    4. Repeats until quality standards are met or max retries reached
    
    The generated article will include:
    - Clear explanations of concepts
    - Step-by-step worked examples at multiple difficulty levels
    - Grade-appropriate vocabulary and sentence structure
    - Properly formatted content with logical organization
    
    The content follows Direct Instruction teaching methodology that emphasizes
    explicit teaching rather than inquiry-based approaches.
    
    Args:
        request: Article generation parameters including lesson, grade level, course, etc.
        article_service: Service for article operations (injected)
        
    Returns:
        ArticleResponse: The generated article
        
    Raises:
        HTTPException: If article generation fails
    """
    try:
        # Use our new generator with grading integration
        article = generate_article_with_grading(
            lesson=request.lesson,
            grade_level=request.grade_level,
            course=request.course,
            difficulty=request.difficulty.value,
            lesson_description=request.lesson_description,
            keywords=request.keywords,
            max_retries=3,  # Default to 3 retries
            metadata={"style": request.style} if request.style else None
        )
        
        return article
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate article: {str(e)}"
        )


@router.post("/grade", response_model=ArticleGradeResponse)
async def grade_article_endpoint(
    request: ArticleGradeRequest
) -> ArticleGradeResponse:
    """
    Grade an educational article based on strict quality criteria.
    
    The grader evaluates the article on eight key criteria:
    - Categorization: Proper subject, grade, standard, lesson categorization
    - Instructional Style: Use of Direct Instruction approach with explicit teaching
    - Worked Examples: Step-by-step examples for all difficulty levels
    - Content Accuracy: Factual correctness and freedom from misconceptions
    - Language Appropriateness: Grade-level vocabulary and sentence structure
    - Clarity: Clear, direct, and unambiguous explanations
    - Formatting: Proper visual organization and layout
    - Content Consistency: Uniform explanations across related lessons
    
    The grader has strict thresholds for quality:
    - Overall passing threshold of 0.85
    - Minimum criterion threshold of 0.75
    - Critical criteria (instructional style, worked examples, content accuracy) 
      must score at least 0.90
    - No critical issues identified
    
    Returns detailed scores, feedback, and any critical issues identified.
    
    Args:
        request: Article grade request containing content and optional metadata
        
    Returns:
        ArticleGradeResponse: Detailed evaluation results
        
    Raises:
        HTTPException: If article grading fails
    """
    try:
        result = grade_article(request.content, request.metadata)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to grade article: {str(e)}"
        ) 