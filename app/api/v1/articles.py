from fastapi import APIRouter, HTTPException, Depends
from typing import List
import uuid
from datetime import datetime

from app.schemas.article import (
    ArticleGenerateRequest, 
    ArticleInDB, 
    ArticleResponse, 
    ArticleGradeRequest, 
    ArticleGradeResponse,
    DifficultyLevel,
    ArticleTagRequest,
    ArticleTagResponse
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
        
    Returns:
        ArticleResponse: The generated article
    """
    try:
        # Use our article generator with grading integration
        print(f"Generating article for lesson: {request.lesson}, grade: {request.grade_level}, course: {request.course}")
        result = generate_article_with_grading(
            lesson=request.lesson,
            grade_level=request.grade_level,
            course=request.course,
            lesson_description=request.lesson_description,
            keywords=request.keywords,
            max_retries=3  # Default to 3 retries
        )
        
        print(f"Article generated successfully: {result.get('title', 'No title')}")
        
        # Set default difficulty_level if not provided
        difficulty_level = result.get('difficulty_level')
        if difficulty_level is None:
            difficulty_level = DifficultyLevel.INTERMEDIATE
        
        # Convert from the raw result to the expected response format
        article_response = ArticleResponse(
            id=result.get('id', str(uuid.uuid4())),
            title=result.get('title', f"Article about {request.lesson}"),
            content=result.get('content', ""),
            grade_level=result.get('grade_level', request.grade_level),
            subject=result.get('course', request.course),  # Map course to subject
            created_at=result.get('created_at', datetime.now().isoformat()),
            updated_at=result.get('updated_at', datetime.now().isoformat()),
            tags=result.get('tags', request.keywords if request.keywords else []),
            quality_score=result.get('quality_score', None),
            readability_score=result.get('readability_score', None),
            difficulty_level=difficulty_level,
            key_concepts=result.get('key_concepts', []),
            examples=result.get('examples', []),
            target_age_range=result.get('target_age_range', [request.grade_level + 4, request.grade_level + 6])
        )
        
        return article_response
        
    except Exception as e:
        import traceback
        print(f"Error generating article: {str(e)}")
        print(traceback.format_exc())
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


@router.post("/tag", response_model=ArticleTagResponse)
async def tag_article_endpoint(
    request: ArticleTagRequest
) -> ArticleTagResponse:
    """
    Tag an article with subject, grade, standard, lesson, and difficulty.
    This endpoint is not yet implemented.
    
    Args:
        request: Article tag request containing content and optional metadata
        
    Returns:
        ArticleTagResponse: Tagging results
        
    Raises:
        HTTPException: If article tagging fails
    """
    return {
        "message": "This endpoint is not yet implemented"
    } 