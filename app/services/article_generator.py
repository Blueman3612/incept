import os
import logging
import openai
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid

from app.services.article_grader import grade_article, preprocess_article_content

logger = logging.getLogger(__name__)

class ArticleGenerator:
    """
    Generates high-quality educational articles that meet strict quality criteria.
    Uses OpenAI's GPT-4 for generation and iteratively improves articles based on grader feedback.
    """
    
    def __init__(self):
        """Initialize the ArticleGenerator with API settings."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable.")
        
        self.model = os.getenv("GPT_MODEL", "gpt-4")
        
        # Templates for worked examples difficulty levels
        self.example_templates = {
            "easy": "A simple example that introduces core concepts with explicit steps.",
            "medium": "An example that combines multiple concepts with detailed explanation of each step.",
            "hard": "A complex example that builds on earlier concepts and challenges students to follow multi-step processes."
        }
        
        # Formatting templates
        self.section_templates = [
            {"intro": "Introduction", "concept": "Key Concept", "examples": "Worked Examples", "practice": "Practice", "summary": "Summary"},
            {"intro": "Let's Learn About", "concept": "Understanding", "examples": "Step-by-Step Examples", "practice": "Your Turn", "summary": "Remember"},
            {"intro": "Exploring", "concept": "Main Idea", "examples": "Watch How It's Done", "practice": "Try These", "summary": "Key Points"}
        ]
    
    def generate_article(self, 
                        topic: str,
                        grade_level: int, 
                        subject: str,
                        difficulty: str,
                        keywords: Optional[List[str]] = None,
                        max_retries: int = 3,
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generates a high-quality educational article.
        
        Args:
            topic: Main topic of the article
            grade_level: Target grade level (1-8)
            subject: Subject area (e.g., "Language Arts")
            difficulty: Difficulty level (e.g., "beginner", "intermediate", "advanced")
            keywords: Optional list of keywords to include
            max_retries: Maximum number of improvement attempts
            metadata: Additional metadata for the grader
            
        Returns:
            Dictionary containing the generated article and metadata
        """
        logger.info(f"Generating article on '{topic}' for Grade {grade_level} {subject} ({difficulty} level)")
        
        # Prepare metadata for grading
        if metadata is None:
            metadata = {}
        
        grading_metadata = {
            "grade_level": grade_level,
            "subject": subject,
            **metadata
        }
        
        # Generate initial article
        article_content = self._generate_initial_article(
            topic=topic,
            grade_level=grade_level,
            subject=subject,
            difficulty=difficulty,
            keywords=keywords or []
        )
        
        best_content = article_content
        best_result = grade_article(article_content, grading_metadata)
        best_score = best_result.get("overall_score", 0)
        
        logger.info(f"Initial article generation complete. Score: {best_score:.2f}, Passing: {best_result.get('passing', False)}")
        
        # If not passing, try to improve it
        retry_count = 0
        while not best_result.get("passing", False) and retry_count < max_retries:
            retry_count += 1
            logger.info(f"Attempting article improvement (try {retry_count}/{max_retries})")
            
            # Extract feedback for improvement
            improvement_feedback = self._extract_improvement_feedback(best_result)
            
            # Generate improved version
            improved_content = self._generate_improved_article(
                topic=topic,
                grade_level=grade_level,
                subject=subject,
                difficulty=difficulty,
                original_content=best_content,
                feedback=improvement_feedback,
                keywords=keywords or []
            )
            
            # Grade the improved version
            improved_result = grade_article(improved_content, grading_metadata)
            improved_score = improved_result.get("overall_score", 0)
            
            logger.info(f"Improved article. New score: {improved_score:.2f}, Passing: {improved_result.get('passing', False)}")
            
            # Check if it's better
            if self._is_better_result(improved_result, best_result):
                best_content = improved_content
                best_result = improved_result
                best_score = improved_score
                logger.info(f"Accepted improved version with score {best_score:.2f}")
        
        # Generate a title
        title = self._generate_title(best_content, topic, grade_level, subject)
        
        # Format the final response
        return {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": best_content,
            "grade_level": grade_level,
            "subject": subject,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tags": keywords or [],
            "quality_score": best_score,
            "readability_score": None,  # Could add readability calculation
            "difficulty_level": difficulty,
            "key_concepts": self._extract_key_concepts(best_content),
            "examples": self._extract_examples(best_content)
        }
    
    def _generate_initial_article(self, 
                                topic: str,
                                grade_level: int,
                                subject: str,
                                difficulty: str,
                                keywords: List[str]) -> str:
        """
        Generates the initial article draft.
        
        Args:
            topic: Main topic of the article
            grade_level: Target grade level
            subject: Subject area
            difficulty: Difficulty level
            keywords: List of keywords to include
            
        Returns:
            Generated article content
        """
        # Select a random section template for variety
        sections = random.choice(self.section_templates)
        
        # Build the prompt
        prompt = f"""
Generate a Grade {grade_level} {subject} educational article on "{topic}" at {difficulty} difficulty level.

IMPORTANT: This must follow Direct Instruction teaching style with these characteristics:
1. Explicitly teach concepts with clear, direct language
2. Break down complex ideas into manageable steps
3. Include worked examples that students can follow step-by-step
4. Use grade-appropriate vocabulary and sentence structure
5. Organize content logically with clear headings and sections

ARTICLE STRUCTURE:
- {sections['intro']}: Briefly introduce the topic and why it's important
- {sections['concept']}: Clearly explain the main concepts with definitions
- {sections['examples']}: Provide 3 worked examples (easy, medium, and hard difficulty)
  • Break down each example into explicit steps
  • Explain the reasoning for each step in detail
  • Use simple language and consistent terminology
- {sections['practice']}: Offer 2-3 practice problems for students to try
- {sections['summary']}: Summarize the key ideas and connect to future learning

CONTENT REQUIREMENTS:
- Target Grade Level: {grade_level}
- Subject: {subject}
- Topic: {topic}
- Difficulty: {difficulty}
- Include these keywords: {', '.join(keywords)}
- Factually accurate information only
- Clear and unambiguous wording
- Content appropriate for students with lower working memory

FORMAT REQUIREMENTS:
- Use headings for each section
- Use bullet points or numbered lists for steps
- Break text into short paragraphs
- Include visual cues like bold text for important concepts

The article should prepare students to answer questions of varying difficulty levels about {topic}.
"""
        
        # Generate the content
        return self._generate_with_gpt(prompt)
    
    def _generate_improved_article(self,
                                  topic: str,
                                  grade_level: int,
                                  subject: str,
                                  difficulty: str,
                                  original_content: str,
                                  feedback: str,
                                  keywords: List[str]) -> str:
        """
        Generates an improved version of the article based on grader feedback.
        
        Args:
            topic: Main topic of the article
            grade_level: Target grade level
            subject: Subject area
            difficulty: Difficulty level
            original_content: Original article content
            feedback: Feedback from the grader
            keywords: Keywords to include
            
        Returns:
            Improved article content
        """
        prompt = f"""
You're an expert educator specializing in Direct Instruction. I need you to improve this Grade {grade_level} {subject} article on "{topic}".

The article has been evaluated and needs improvement based on this feedback:

{feedback}

Original Article:
```
{original_content}
```

REVISION INSTRUCTIONS:
1. Fix all the identified issues while preserving the overall structure
2. Ensure the article strictly follows Direct Instruction style
3. Make sure worked examples are broken down into very clear steps
4. Maintain grade-appropriate vocabulary and sentence structure
5. Ensure all content is factually accurate
6. Keep the article focused on the topic: "{topic}"
7. Include these keywords: {', '.join(keywords)}

IMPORTANT:
- Do NOT change the overall educational purpose
- Do NOT add unnecessary complexity
- Do NOT use inquiry-based learning approaches
- KEEP the Direct Instruction style with explicit teaching

Return the complete improved article maintaining proper formatting with headings, lists, and paragraph breaks.
"""
        
        # Generate the improved content
        return self._generate_with_gpt(prompt)
    
    def _extract_improvement_feedback(self, grading_result: Dict[str, Any]) -> str:
        """
        Extracts actionable feedback from grading results.
        
        Args:
            grading_result: Grading results dictionary
            
        Returns:
            Formatted feedback string
        """
        feedback = "AREAS TO IMPROVE:\n"
        
        # Add critical issues first
        if grading_result.get("critical_issues"):
            feedback += "CRITICAL ISSUES:\n"
            for issue in grading_result.get("critical_issues", []):
                feedback += f"- {issue}\n"
            feedback += "\n"
        
        # Add criterion-specific feedback for low scores
        criterion_scores = grading_result.get("criterion_scores", {})
        criterion_feedback = grading_result.get("criterion_feedback", {})
        
        for criterion, score in criterion_scores.items():
            if score < 0.85:
                criterion_name = criterion.replace('_', ' ').title()
                feedback += f"{criterion_name} ({score:.2f}):\n"
                feedback += f"- {criterion_feedback.get(criterion, 'No specific feedback')}\n\n"
        
        # Add overall feedback
        feedback += "\nOVERALL GUIDANCE:\n"
        feedback += grading_result.get("feedback", "Improve the article based on the issues identified above.")
        
        return feedback
    
    def _is_better_result(self, current: Dict[str, Any], best: Dict[str, Any]) -> bool:
        """
        Determines if the current result is better than the best result so far.
        
        Args:
            current: Current grading result
            best: Best grading result so far
            
        Returns:
            Boolean indicating if current is better than best
        """
        # If the current result passes and the best doesn't, it's better
        if current.get("passing", False) and not best.get("passing", False):
            return True
        
        # If both pass or both fail, compare scores
        current_score = current.get("overall_score", 0)
        best_score = best.get("overall_score", 0)
        
        # If scores are close, check critical criteria
        if abs(current_score - best_score) < 0.05:
            # Check critical criteria scores
            current_critical_avg = sum(current.get("criterion_scores", {}).get(c, 0) 
                                      for c in ["instructional_style", "worked_examples", "content_accuracy"]) / 3
            best_critical_avg = sum(best.get("criterion_scores", {}).get(c, 0) 
                                   for c in ["instructional_style", "worked_examples", "content_accuracy"]) / 3
            
            return current_critical_avg > best_critical_avg
        
        # Otherwise use overall score
        return current_score > best_score
    
    def _generate_title(self, content: str, topic: str, grade_level: int, subject: str) -> str:
        """
        Generates an engaging title for the article.
        
        Args:
            content: Article content
            topic: Main topic
            grade_level: Target grade level
            subject: Subject area
            
        Returns:
            Article title
        """
        prompt = f"""
Create a brief, engaging title for a Grade {grade_level} {subject} educational article on "{topic}".
The title should be:
1. Clear and descriptive
2. No more than 8 words
3. Appropriate for Grade {grade_level} students
4. Related directly to the core concept being taught

Article content:
```
{content[:500]}...
```

Return ONLY the title with no additional text, quotation marks, or explanation.
"""
        
        title = self._generate_with_gpt(prompt).strip()
        
        # Remove any quotes
        title = title.replace('"', '').replace("'", "").strip()
        
        # Limit length
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """
        Extracts key concepts from the article content.
        
        Args:
            content: Article content
            
        Returns:
            List of key concepts
        """
        prompt = f"""
Extract 3-5 key concepts taught in this educational article:

```
{content[:2000]}
```

Return ONLY a comma-separated list of concepts, with no numbering or additional text.
"""
        
        concepts_text = self._generate_with_gpt(prompt).strip()
        
        # Split by commas and clean up
        concepts = [concept.strip() for concept in concepts_text.split(',') if concept.strip()]
        
        # Limit to 5 concepts
        return concepts[:5]
    
    def _extract_examples(self, content: str) -> List[str]:
        """
        Extracts worked examples from the article content.
        
        Args:
            content: Article content
            
        Returns:
            List of examples
        """
        prompt = f"""
Extract the titles or first sentences of each worked example in this educational article:

```
{content[:2000]}
```

Return ONLY a comma-separated list of example descriptions, with no numbering or additional text.
"""
        
        examples_text = self._generate_with_gpt(prompt).strip()
        
        # Split by commas and clean up
        examples = [example.strip() for example in examples_text.split(',') if example.strip()]
        
        # Limit to 5 examples
        return examples[:5]
    
    def _generate_with_gpt(self, prompt: str) -> str:
        """
        Generates content using GPT.
        
        Args:
            prompt: Generation prompt
            
        Returns:
            Generated content
        """
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert education content creator specializing in Direct Instruction teaching methods and Grade K-8 curriculum development."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2500
            )
            
            content = response.choices[0].message.content
            return preprocess_article_content(content)
            
        except Exception as e:
            logger.error(f"Error in GPT generation: {str(e)}")
            raise ValueError(f"Failed to generate content: {str(e)}")


def generate_article_with_grading(
    topic: str,
    grade_level: int, 
    subject: str,
    difficulty: str,
    keywords: Optional[List[str]] = None,
    max_retries: int = 3,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main function to generate a high-quality article that passes quality checks.
    
    Args:
        topic: Main topic of the article
        grade_level: Target grade level (1-8)
        subject: Subject area (e.g., "Language Arts")
        difficulty: Difficulty level (e.g., "beginner", "intermediate", "advanced")
        keywords: Optional list of keywords to include
        max_retries: Maximum number of improvement attempts
        metadata: Additional metadata for the grader
        
    Returns:
        Dictionary containing the generated article and metadata
    """
    generator = ArticleGenerator()
    return generator.generate_article(
        topic=topic,
        grade_level=grade_level,
        subject=subject,
        difficulty=difficulty,
        keywords=keywords,
        max_retries=max_retries,
        metadata=metadata
    ) 