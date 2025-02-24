from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.schemas.article import ArticleGenerateRequest, ArticleResponse
from app.services.article_service import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("/generate", response_model=ArticleResponse)
async def generate_article(
    request: ArticleGenerateRequest,
    article_service: ArticleService = Depends(lambda: ArticleService())
) -> ArticleResponse:
    """
    Generate an educational article based on the provided parameters.
    
    Args:
        request (ArticleGenerateRequest): The article generation request parameters
        article_service (ArticleService): The article service instance
        
    Returns:
        ArticleResponse: The generated article
        
    Raises:
        HTTPException: If article generation fails
    """
    try:
        article = await article_service.generate_article(request)
        return ArticleResponse.model_validate(article)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate article: {str(e)}"
        ) 