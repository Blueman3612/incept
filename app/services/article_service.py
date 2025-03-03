from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import json
import logging
from postgrest.exceptions import APIError

from app.schemas.article import ArticleGenerateRequest, ArticleInDB, DifficultyLevel
from app.db.base import get_supabase
from app.services.openai_service import OpenAIService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleService:
    """Service for handling article-related operations."""

    def __init__(self):
        try:
            self.supabase = get_supabase()
            logger.info("Successfully initialized Supabase client")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            self.supabase = None
        self.openai_service = OpenAIService()

    async def generate_article(self, request: ArticleGenerateRequest) -> ArticleInDB:
        """
        Generate a high-quality educational article.
        
        Args:
            request (ArticleGenerateRequest): The article generation request parameters
            
        Returns:
            ArticleInDB: The generated article
        """
        try:
            # Generate article content using the external service
            article_data = generate_article_with_grading(
                lesson=request.lesson,
                grade_level=request.grade_level,
                course=request.course,
                difficulty=request.difficulty.value,
                lesson_description=request.lesson_description,
                keywords=request.keywords,
                max_retries=3  # Default to 3 improvement attempts
            )
            
            # Convert to ArticleInDB model
            article = ArticleInDB(
                id=str(uuid.uuid4()),
                title=article_data.get('title', f"Article on {request.lesson}"),
                content=article_data.get('content', ''),
                grade_level=request.grade_level,
                subject=request.course,  # Map course to subject for database compatibility
                tags=request.keywords,
                difficulty_level=request.difficulty,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                target_age_range=self._grade_to_age_range(request.grade_level),
                quality_score=article_data.get('quality_score'),
                readability_score=None,  # Could add readability calculation
                key_concepts=article_data.get('key_concepts', []),
                examples=article_data.get('examples', [])
            )
            
            # Store the article
            await self._store_article(article)
            
            logger.info(f"Generated article: {article.id} - {article.title}")
            return article
            
        except Exception as e:
            logger.error(f"Error generating article: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate article: {str(e)}")

    async def _store_article(self, article: ArticleInDB) -> None:
        """
        Store the article in Supabase.
        
        Args:
            article (ArticleInDB): The article to store
            
        Raises:
            Exception: If storage operation fails
        """
        try:
            data = article.model_dump()
            # Convert datetime objects to ISO format strings
            data["created_at"] = data["created_at"].isoformat()
            data["updated_at"] = data["updated_at"].isoformat()
            # Convert enum to string
            data["difficulty_level"] = data["difficulty_level"].value
            
            # Log the data being sent to Supabase
            logger.debug("Preparing to store article in Supabase")
            logger.debug(f"Article data: {json.dumps(data, indent=2)}")
            
            try:
                # Insert data into Supabase
                result = self.supabase.table("articles").insert(data).execute()
                
                if not result.data:
                    raise Exception("No data returned from Supabase insert operation")
                    
                logger.info(f"Successfully stored article in Supabase with ID: {article.id}")
                logger.debug(f"Supabase response: {json.dumps(result.data, indent=2)}")
                
            except APIError as e:
                logger.error(f"Supabase API error: {str(e)}")
                logger.error(f"Error details: {e.details if hasattr(e, 'details') else 'No details available'}")
                raise Exception(f"Supabase API error: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error storing article in database: {str(e)}")
            raise Exception(f"Error storing article in database: {str(e)}") 