import os
from openai import OpenAI
from typing import Dict, Any
from app.schemas.article import ArticleGenerateRequest, DifficultyLevel

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
                        and key concepts that students should understand."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return {
                "content": response.choices[0].message.content,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
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
        
        Format the response in the following JSON structure:
        {{
            "title": "Article Title",
            "content": "Main article content with clear paragraphs",
            "key_concepts": ["concept1", "concept2", "concept3"],
            "examples": ["example1", "example2", "example3"]
        }}
        """
        return prompt.strip() 