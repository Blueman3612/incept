from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.schemas.article import ArticleGenerateRequest, ArticleInDB, ArticleResponse
from app.services.article_service import ArticleService

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
    
    Args:
        request: Article generation parameters including topic, grade level, etc.
        article_service: Service for article operations (injected)
        
    Returns:
        ArticleResponse: The generated article
        
    Raises:
        HTTPException: If article generation fails
    """
    try:
        article = await article_service.generate_article(request)
        return article
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate article: {str(e)}"
        ) 