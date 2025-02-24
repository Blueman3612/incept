from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import json
import logging

from app.schemas.article import ArticleGenerateRequest, ArticleInDB, DifficultyLevel
from app.db.base import get_supabase
from app.services.openai_service import OpenAIService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArticleService:
    """Service for handling article-related operations."""

    def __init__(self):
        self.supabase = get_supabase()
        self.openai_service = OpenAIService()

    async def generate_article(self, request: ArticleGenerateRequest) -> ArticleInDB:
        """
        Generate an educational article based on the provided parameters.
        
        Args:
            request (ArticleGenerateRequest): The article generation request parameters
            
        Returns:
            ArticleInDB: The generated article
        
        Raises:
            Exception: If article generation or storage fails
        """
        try:
            # Generate article content using OpenAI
            generated_content = await self.openai_service.generate_educational_article(request)
            
            # Parse the JSON response
            content_data = json.loads(generated_content["content"])
            logger.info(f"Successfully generated content for topic: {request.topic}")
            
            # Create article record
            article = ArticleInDB(
                id=str(uuid.uuid4()),
                title=content_data["title"],
                content=content_data["content"],
                grade_level=request.grade_level,
                subject=request.subject,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                tags=request.keywords or [],
                quality_score=None,  # To be implemented with content evaluation
                readability_score=None,  # To be implemented with readability analysis
                difficulty_level=request.difficulty,
                key_concepts=content_data["key_concepts"],
                examples=content_data["examples"]
            )
            
            # For testing, return the article without storing if Supabase is not configured
            if not self.supabase:
                logger.warning("Supabase not configured, skipping storage")
                return article

            # Store in Supabase
            try:
                await self._store_article(article)
                logger.info(f"Successfully stored article with ID: {article.id}")
            except Exception as e:
                logger.error(f"Failed to store article in database: {str(e)}")
                # Return the generated article even if storage fails
                return article
            
            return article
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing generated content: {str(e)}")
            raise Exception(f"Error parsing generated content: {str(e)}")
        except Exception as e:
            logger.error(f"Error in article generation process: {str(e)}")
            raise Exception(f"Error in article generation process: {str(e)}")

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
            logger.debug(f"Attempting to store article data: {data}")
            
            # Insert data into Supabase
            result = self.supabase.table("articles").insert(data).execute()
            
            if not result.data:
                raise Exception("No data returned from Supabase insert operation")
                
            logger.info(f"Successfully stored article in Supabase with ID: {article.id}")
            
        except Exception as e:
            logger.error(f"Error storing article in database: {str(e)}")
            raise Exception(f"Error storing article in database: {str(e)}") 