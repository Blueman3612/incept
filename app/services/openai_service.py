import os
from openai import OpenAI
from typing import Dict, Any

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("GPT_MODEL", "gpt-4-turbo-preview")

    async def generate_educational_content(
        self,
        topic: str,
        grade_level: str,
        content_type: str,
        additional_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        Generate educational content using GPT-4.
        
        Args:
            topic: The main topic for the content
            grade_level: Target grade level (K-8)
            content_type: Type of content (article, quiz, lesson_plan, etc.)
            additional_instructions: Any specific requirements or instructions
            
        Returns:
            Dict containing the generated content and metadata
        """
        prompt = self._create_prompt(topic, grade_level, content_type, additional_instructions)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert educational content creator, specializing in K-8 education. Your content is engaging, age-appropriate, and aligned with educational standards."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return {
                "content": response.choices[0].message.content,
                "topic": topic,
                "grade_level": grade_level,
                "content_type": content_type,
                "model_used": self.model,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            raise Exception(f"Error generating content: {str(e)}")
    
    def _create_prompt(
        self,
        topic: str,
        grade_level: str,
        content_type: str,
        additional_instructions: str
    ) -> str:
        """Create a detailed prompt for the AI model."""
        base_prompt = f"""
        Create {content_type} about {topic} for grade {grade_level} students.
        
        Requirements:
        - Content should be engaging and interactive
        - Use age-appropriate language and examples
        - Include real-world applications where relevant
        - Ensure accuracy and educational value
        - Format the content in a clear, structured way
        
        {additional_instructions}
        """
        return base_prompt.strip() 