import os
from openai import AsyncOpenAI
from typing import Dict, Any
import json
import logging
from app.schemas.article import ArticleGenerateRequest, DifficultyLevel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("GPT_MODEL", "gpt-4-turbo-preview")

    async def generate_educational_article(
        self,
        request: ArticleGenerateRequest
    ) -> Dict[str, Any]:
        """
        Generate an educational article using GPT-4.
        
        Args:
            request: The article generation request containing topic, grade level, etc.
            
        Returns:
            Dict containing the generated article content and metadata
        """
        prompt = self._create_article_prompt(request)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert educational content creator, specializing in K-8 education.
                        Your content is engaging, age-appropriate, and aligned with educational standards.
                        You create well-structured articles that include clear explanations, relevant examples,
                        and key concepts that students should understand.
                        
                        IMPORTANT: Your response must be valid JSON with no control characters or special formatting.
                        Use regular quotes (") for JSON strings and escape any quotes within the content.
                        Do not include any text before or after the JSON object."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Get the response content
            content = response.choices[0].message.content.strip()
            
            # Validate JSON structure
            try:
                parsed_content = json.loads(content)
                required_fields = ["title", "content", "key_concepts", "examples"]
                for field in required_fields:
                    if field not in parsed_content:
                        raise ValueError(f"Missing required field: {field}")
                if not isinstance(parsed_content["key_concepts"], list):
                    raise ValueError("key_concepts must be a list")
                if not isinstance(parsed_content["examples"], list):
                    raise ValueError("examples must be a list")
                
                # Clean up any potential issues with the content
                parsed_content["content"] = parsed_content["content"].replace("\r", "")
                content = json.dumps(parsed_content)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in response: {content}")
                raise ValueError(f"OpenAI response was not valid JSON: {str(e)}")
            except ValueError as e:
                logger.error(f"Invalid response structure: {content}")
                raise ValueError(f"Invalid response structure: {str(e)}")
            
            return {
                "content": content,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Error generating article: {str(e)}")
            raise Exception(f"Error generating article: {str(e)}")
    
    def _create_article_prompt(self, request: ArticleGenerateRequest) -> str:
        """Create a detailed prompt for article generation."""
        grade_appropriate_terms = {
            "beginner": "simple and basic",
            "intermediate": "moderately complex",
            "advanced": "challenging and in-depth"
        }

        difficulty_level = grade_appropriate_terms[request.difficulty.value]
        
        prompt = f"""
        Create an educational article about {request.topic} for grade {request.grade_level} students.
        The content should be {difficulty_level} for this grade level.
        
        Subject Area: {request.subject}
        Writing Style: {request.style}
        
        Required Structure:
        1. Title: Create an engaging, age-appropriate title
        2. Introduction: Brief, engaging overview of the topic
        3. Main Content: Clear explanations with {difficulty_level} concepts
        4. Examples: 2-3 practical, real-world examples that students can relate to
        5. Key Concepts: List 3-5 important concepts students should remember
        
        Requirements:
        - Use age-appropriate language for grade {request.grade_level}
        - Make content engaging and interactive
        - Include real-world applications
        - Ensure scientific/factual accuracy
        - Break down complex ideas into manageable parts
        
        Keywords to include: {', '.join(request.keywords) if request.keywords else 'No specific keywords required'}
        
        Respond ONLY with a valid JSON object using this exact structure:
        {{
            "title": "Your engaging title here",
            "content": "Your main article content here, with proper paragraph breaks using \\n",
            "key_concepts": ["concept1", "concept2", "concept3"],
            "examples": ["example1", "example2", "example3"]
        }}
        
        IMPORTANT: 
        1. Your entire response must be a single JSON object
        2. Do not include any text before or after the JSON
        3. Use proper escaping for quotes and newlines
        4. Use only plain text with \n for line breaks
        5. Make sure the JSON is valid and can be parsed
        """
        return prompt.strip() 