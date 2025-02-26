"""
Question Generator Service

This service is responsible for generating high-quality educational questions
that pass our strict quality criteria. The service leverages our grader service
to evaluate generated questions and improve them based on feedback.

The service supports:
1. Generating new questions based on topic, difficulty, etc.
2. Creating variations of existing questions
3. Using feedback to iteratively improve questions until they meet quality standards
"""

import os
import json
import logging
import time
import random
import requests
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
from app.services.grader_service import grade_question

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('question_generator.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class QuestionGenerator:
    """
    Generates high-quality educational questions that pass quality standards.
    Uses feedback from the grader service to improve questions iteratively.
    """
    
    def __init__(self):
        """Initialize the QuestionGenerator with API settings."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable.")
        
        self.model = os.getenv("GPT_MODEL", "gpt-4")
        
        # Set up context options for variety in question generation
        self.contexts = [
            "a student's experience at school",
            "an interesting animal fact",
            "a historical event",
            "a scientific discovery",
            "a community event",
            "a family tradition",
            "a nature observation",
            "a problem-solving situation",
            "a cultural celebration",
            "a creative activity"
        ]
        
        # Question structure templates for variety
        self.structures = [
            "a main idea question",
            "a supporting details question",
            "a compare and contrast question",
            "a cause and effect question",
            "a vocabulary in context question",
            "a sequencing question",
            "an inference question",
            "a character trait question",
            "an author's purpose question",
            "a fact vs. opinion question"
        ]
        
        # Specific kid-friendly topics for greater variety in passage content
        self.topics = [
            # Animals
            "pandas and their bamboo diet",
            "how chameleons change colors",
            "dolphins and their communication methods",
            "the migration of monarch butterflies",
            "how beavers build dams",
            "pet care responsibilities",
            "unusual ocean creatures",
            "how birds build nests",
            "fascinating insect behaviors",
            "amazing animal adaptations",
            
            # Science & Nature
            "how rainbows form in the sky",
            "the water cycle",
            "different types of clouds",
            "how plants grow from seeds",
            "volcanoes and how they erupt",
            "the changing seasons",
            "recycling and caring for the environment",
            "the solar system planets",
            "how weather forecasting works",
            "dinosaur discoveries",
            
            # Daily Life & Social Studies
            "planning a school garden",
            "organizing a community cleanup",
            "how to start a hobby collection",
            "planning a special birthday party",
            "making friends in a new school",
            "learning a new skill or sport",
            "saving money for something special",
            "helping in your community",
            "cultures around the world",
            "family holiday traditions",
            
            # History & People
            "the first trip to the moon",
            "important inventions like the telephone",
            "how transportation has changed over time",
            "early explorers and their discoveries",
            "how people lived long ago",
            "the history of your favorite foods",
            "famous artists and their work",
            "people who made a difference in history",
            "ancient civilizations",
            "how schools were different in the past",
            
            # Stories & Adventures
            "a camping adventure in the woods",
            "discovering a hidden treasure map",
            "making an unexpected friend",
            "overcoming a fear",
            "solving a neighborhood mystery",
            "creating an invention",
            "helping someone in need",
            "participating in a competition",
            "exploring a new place",
            "learning something surprising"
        ]
        
        logger.info("QuestionGenerator initialized with model: %s", self.model)
    
    def generate_question(self, 
                        lesson: str, 
                        difficulty: str, 
                        example_question: Optional[str] = None,
                        max_retries: int = 1,
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a high-quality question that passes our grader.
        
        Args:
            lesson: The lesson topic (e.g., "main_idea", "supporting_details")
            difficulty: Difficulty level ("easy", "medium", "hard")
            example_question: Optional example to create a variation from
            max_retries: Maximum number of improvement attempts if question fails
            metadata: Additional metadata to pass to the grader (e.g., grade_level)
            
        Returns:
            Dict containing the generated question, quality assessment, and metadata
        """
        logger.info(f"Generating question for lesson: {lesson}, difficulty: {difficulty}")
        logger.info(f"Max retries: {max_retries}, Example provided: {example_question is not None}")
        
        # Set default metadata if not provided
        if metadata is None:
            metadata = {"grade_level": 4, "subject": "Language Arts"}
        
        # Generate initial question
        question_content = self._generate_initial_question(lesson, difficulty, example_question)
        
        # Grade the initial question
        grading_result = grade_question(question_content, metadata)
        logger.info(f"Initial question grading: {grading_result['overall_result']}")
        logger.info(f"Scores: {json.dumps(grading_result['scores'], indent=2)}")
        
        attempt = 0
        best_result = grading_result
        best_content = question_content
        
        # If the question failed, try to improve it based on feedback
        while (grading_result['overall_result'] == 'fail' and attempt < max_retries):
            attempt += 1
            logger.info(f"Attempt {attempt}/{max_retries} to improve question")
            
            # Extract feedback to improve the question
            feedback = self._extract_improvement_feedback(grading_result)
            logger.info(f"Improvement feedback: {feedback}")
            
            # Generate improved question using feedback
            question_content = self._generate_improved_question(
                lesson, difficulty, question_content, feedback, example_question
            )
            
            # Grade the improved question
            grading_result = grade_question(question_content, metadata)
            logger.info(f"Improved question grading: {grading_result['overall_result']}")
            logger.info(f"Scores: {json.dumps(grading_result['scores'], indent=2)}")
            
            # Keep track of the best result so far
            if self._is_better_result(grading_result, best_result):
                best_result = grading_result
                best_content = question_content
        
        # Prepare the final response with the best question and its assessment
        result = {
            "content": best_content,
            "quality": {
                "passed": best_result["overall_result"] == "pass",
                "scores": best_result["scores"],
                "overall_score": sum(best_result["scores"].values()) / len(best_result["scores"]),
                "failed_criteria": [
                    k for k, v in best_result["criteria_results"].items() if not v
                ],
                "feedback": best_result["feedback"] if best_result["overall_result"] == "fail" else None
            },
            "metadata": {
                "lesson": lesson,
                "difficulty": difficulty,
                "attempts": attempt + 1,
                "based_on_example": example_question is not None,
                "critical_issues": best_result.get("critical_issues", [])
            }
        }
        
        logger.info(f"Question generation complete. Success: {result['quality']['passed']}")
        return result
    
    def _generate_initial_question(self, lesson: str, difficulty: str, example_question: Optional[str] = None) -> str:
        """
        Generate the initial question content either from scratch or based on an example.
        
        Args:
            lesson: The lesson topic
            difficulty: Difficulty level
            example_question: Optional example to base the question on
            
        Returns:
            Generated question content
        """
        # Common language guidelines for grade 4
        language_guidance = """
LANGUAGE GUIDELINES FOR GRADE 4:
- Use vocabulary appropriate for 9-10 year olds
- Keep sentences under 15 words when possible
- Use clear, direct language without ambiguity
- Be historically and factually accurate
- Each wrong answer explanation must be educational and complete
- Solution steps should be clear and sequential
"""
        
        # Handle variation generation if example_question is provided
        if example_question:
            logger.info("Generating a variation based on example question")
            prompt = f"""Generate a Grade 4 Language Arts question variation for the lesson on "{lesson}" at {difficulty} difficulty level.
This is based on the following example question:

{example_question}

{language_guidance}

IMPORTANT REQUIREMENTS:
1. Keep the same general structure and question type
2. Create a DIFFERENT passage with similar complexity
3. Maintain the same difficulty level ({difficulty})
4. Use the same number of options
5. Keep all the required parts: passage, question, options, explanations, and solution
6. Ensure there is ONE unambiguously correct answer

FORMAT THE QUESTION EXACTLY LIKE THE EXAMPLE ABOVE but with new content.
"""
        else:
            # Create a new question from scratch
            logger.info("Generating a new question from scratch")
            #selected_context = random.choice(self.contexts)
            selected_structure = random.choice(self.structures)
            selected_topic = random.choice(self.topics)
            
            prompt = f"""Generate a high-quality Grade 4 Language Arts question for the lesson on "{lesson}" at {difficulty} difficulty level.

{language_guidance}

Content Requirements:
1. Write a passage about {selected_topic}
2. Use {selected_structure} for your question
3. Create 4 multiple choice options labeled A, B, C, and D
4. Include COMPLETE explanations for each wrong answer
5. Provide a step-by-step solution with 3-4 steps
6. Ensure there is ONE unambiguously correct answer

FORMAT THE QUESTION EXACTLY LIKE THIS:
Read the following passage and answer the question.

[Write a grade-appropriate passage with short sentences]

[Clear, unambiguous question]

A) [Option]
B) [Option]
C) [Option]
D) [Option]

Correct Answer: [Letter]

Explanation for wrong answers:
A) [If incorrect: Clear explanation why this is wrong - must be a complete thought]
B) [If incorrect: Clear explanation why this is wrong - must be a complete thought]
C) [If incorrect: Clear explanation why this is wrong - must be a complete thought]
D) [If incorrect: Clear explanation why this is wrong - must be a complete thought]

Solution:
1. [Simple step]
2. [Simple step]
3. [Simple step]
4. [Optional simple step]"""
        
        # Generate content using OpenAI
        logger.info(f"Sending generation prompt to {self.model}")
        return self._generate_with_gpt(prompt)
    
    def _extract_improvement_feedback(self, grading_result: Dict[str, Any]) -> str:
        """
        Extract actionable feedback from grading results to improve the question.
        
        Args:
            grading_result: The grading results from the grader service
            
        Returns:
            Consolidated feedback string for improvement
        """
        feedback_str = "Improve the following aspects of the question:\n\n"
        
        # Add feedback for each failed criterion
        for criterion, passes in grading_result["criteria_results"].items():
            if not passes:
                criterion_feedback = grading_result["feedback"].get(criterion, "")
                feedback_str += f"- {criterion.upper()}: {criterion_feedback}\n"
        
        # Add any critical issues
        if grading_result.get("critical_issues"):
            feedback_str += "\nCritical issues to fix:\n"
            for issue in grading_result["critical_issues"]:
                feedback_str += f"- {issue}\n"
        
        return feedback_str
    
    def _generate_improved_question(self, 
                                 lesson: str, 
                                 difficulty: str, 
                                 original_question: str, 
                                 feedback: str,
                                 example_question: Optional[str] = None) -> str:
        """
        Generate an improved version of the question based on grader feedback.
        
        Args:
            lesson: The lesson topic
            difficulty: Difficulty level
            original_question: The original question content
            feedback: Feedback from the grader
            example_question: Optional example question (for context)
            
        Returns:
            Improved question content
        """
        logger.info("Generating improved question based on feedback")
        
        # If the issue is with the content/topic itself, select a new topic
        selected_topic = random.choice(self.topics)
        
        # Create a detailed prompt for improvement
        prompt = f"""You are an expert educational content developer tasked with improving a Grade 4 Language Arts question.
The question is for a lesson on "{lesson}" at {difficulty} difficulty level.

Here is the original question:
```
{original_question}
```

This question did not meet our quality standards. Please improve it based on this feedback:
{feedback}

IMPORTANT:
1. Keep the same general question type and structure
2. Consider writing about a completely different topic: {selected_topic}
3. Maintain the same difficulty level ({difficulty})
4. Address ALL the feedback points
5. Keep the same basic structure (passage, question, options, explanations, solution)
6. Ensure there is ONE unambiguously correct answer
7. Keep language appropriate for 9-10 year olds
8. Make sure all explanations are complete and educational

Return the complete improved question with all components.
"""
        
        # If we have an example question, add it for reference
        if example_question:
            prompt += f"\n\nFor reference, here is a similar high-quality question you can use as a model:\n```\n{example_question}\n```"
        
        # Generate improved content
        return self._generate_with_gpt(prompt)
    
    def _is_better_result(self, current: Dict[str, Any], best: Dict[str, Any]) -> bool:
        """
        Determine if the current result is better than the previous best result.
        
        Args:
            current: Current grading result
            best: Previous best grading result
            
        Returns:
            True if current is better than best
        """
        # If current passes and best doesn't, current is better
        if current["overall_result"] == "pass" and best["overall_result"] != "pass":
            return True
        
        # If both have the same pass/fail status, compare scores
        if current["overall_result"] == best["overall_result"]:
            current_avg = sum(current["scores"].values()) / len(current["scores"])
            best_avg = sum(best["scores"].values()) / len(best["scores"])
            return current_avg > best_avg
        
        return False
    
    def _generate_with_gpt(self, prompt: str) -> str:
        """
        Generate content using OpenAI's GPT models.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            Generated content from the model
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert educational content creator specializing in Grade 4 Language Arts."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,  # Balance creativity with consistency
                "max_tokens": 2000
            }
            
            start_time = time.time()
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            elapsed_time = time.time() - start_time
            
            logger.info(f"OpenAI API response time: {elapsed_time:.2f} seconds")
            
            if response.status_code != 200:
                error_msg = f"API request failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            tokens_used = result.get("usage", {})
            logger.info(f"Generation complete. Tokens used: {json.dumps(tokens_used)}")
            
            return content
            
        except Exception as e:
            logger.exception(f"Error generating content: {str(e)}")
            raise RuntimeError(f"Failed to generate content: {str(e)}")


# Create a singleton instance for use across the application
question_generator = QuestionGenerator()

def generate_question_with_grading(
    lesson: str, 
    difficulty: str, 
    example_question: Optional[str] = None,
    max_retries: int = 1,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a question for the given parameters that passes our quality standards.
    
    Args:
        lesson: The lesson topic (e.g., "main_idea", "supporting_details")
        difficulty: Difficulty level ("easy", "medium", "hard")
        example_question: Optional example to create a variation from
        max_retries: Maximum number of improvement attempts if question fails
        metadata: Additional metadata to pass to the grader
        
    Returns:
        Dict containing the generated question, quality assessment, and metadata
    """
    return question_generator.generate_question(
        lesson=lesson,
        difficulty=difficulty,
        example_question=example_question,
        max_retries=max_retries,
        metadata=metadata
    ) 