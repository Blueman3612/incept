"""
Test script for the question generator service.

This script tests the ability of the question generator to create high-quality
questions that pass our grading criteria. It provides detailed logging to track
the generation process and the grading results.
"""

import os
import sys
import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add the project root to the path so we can import our app modules
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from app.services.question_generator import generate_question_with_grading
from app.services.grader_service import grade_question
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_generator.log')
    ]
)
logger = logging.getLogger("test_generator")

# Load environment variables
load_dotenv()

def save_result_to_file(result: Dict[str, Any], filename: str) -> None:
    """
    Save test results to a JSON file.
    
    Args:
        result: The generation result dictionary
        filename: Name of the output file
    """
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / filename
    
    # Save the result to a file
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Result saved to {output_path}")

def test_generation_with_parameters(
    lesson: str, 
    difficulty: str, 
    max_retries: int = 1,
    example_question: Optional[str] = None
) -> None:
    """
    Test the question generator with specific parameters.
    
    Args:
        lesson: Lesson topic to generate a question for
        difficulty: Difficulty level (easy, medium, hard)
        max_retries: Number of improvement attempts
        example_question: Optional example question for variation generation
    """
    start_time = time.time()
    
    logger.info(f"Testing question generation for lesson: {lesson}, difficulty: {difficulty}")
    logger.info(f"Max retries: {max_retries}, Example provided: {example_question is not None}")
    
    metadata = {"grade_level": 4, "subject": "Language Arts"}
    
    # Generate the question
    try:
        result = generate_question_with_grading(
            lesson=lesson,
            difficulty=difficulty,
            example_question=example_question,
            max_retries=max_retries,
            metadata=metadata
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Generation completed in {elapsed_time:.2f} seconds")
        
        # Log detailed results
        logger.info(f"Generation successful: {result['quality']['passed']}")
        logger.info(f"Overall score: {result['quality']['overall_score']:.2f}")
        
        scores = result['quality']['scores']
        logger.info("Individual scores:")
        for criterion, score in scores.items():
            logger.info(f"  - {criterion}: {score:.2f}")
        
        if not result['quality']['passed']:
            logger.info("Failed criteria:")
            for criterion in result['quality']['failed_criteria']:
                logger.info(f"  - {criterion}")
        
        # Save the result to a file
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"{lesson}_{difficulty}_{timestamp}.json"
        save_result_to_file(result, filename)
        
        # Print the generated content
        print("\n" + "="*80)
        print(f"GENERATED QUESTION (Lesson: {lesson}, Difficulty: {difficulty})")
        print("="*80)
        print(result['content'])
        print("="*80)
        print(f"Quality Assessment: {'PASSED' if result['quality']['passed'] else 'FAILED'}")
        print(f"Overall Score: {result['quality']['overall_score']:.2f}")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.exception(f"Error during generation: {str(e)}")

def test_with_example() -> None:
    """Test generating a variation based on an example question."""
    example_question = """Read the following passage and answer the question.

James was walking to school one morning when he saw a stray dog. The dog looked hungry and scared. James had his lunch in his backpack. He decided to share his sandwich with the dog. The dog wagged its tail and ate the food quickly. James then continued to school, feeling happy that he had helped the dog.

What is the main idea of this passage?

A) James goes to school every morning.
B) James helped a stray dog by sharing his lunch.
C) The dog was hungry and ate the sandwich quickly.
D) James had a sandwich in his backpack.

Correct Answer: B

Explanation for wrong answers:
A) This is incorrect because while the passage mentions James walking to school, the main focus is on his interaction with the dog, not his daily routine.
B) This is the correct answer because the passage primarily describes how James helped the stray dog by sharing his food with it.
C) This is incorrect because while the passage mentions the dog was hungry and ate quickly, this is a supporting detail, not the main idea of the passage.
D) This is incorrect because having a sandwich in his backpack is just a detail that supports the main action of sharing food with the dog.

Solution:
1. Identify what the passage is mostly about by looking for the central action or theme.
2. The passage describes James seeing a stray dog and choosing to help it by sharing his lunch.
3. The main idea should capture the most important action in the passage: James helping the dog.
4. Answer B correctly summarizes this main idea."""

    test_generation_with_parameters(
        lesson="main_idea",
        difficulty="easy",
        max_retries=1,
        example_question=example_question
    )

def test_batch_generation() -> None:
    """Test a batch of question generations for different topics."""
    test_cases = [
        {"lesson": "main_idea", "difficulty": "easy", "max_retries": 1},
        {"lesson": "supporting_details", "difficulty": "medium", "max_retries": 1},
        {"lesson": "authors_purpose", "difficulty": "hard", "max_retries": 2},
        {"lesson": "vocabulary_context", "difficulty": "easy", "max_retries": 1},
        {"lesson": "compare_contrast", "difficulty": "medium", "max_retries": 1}
    ]
    
    for case in test_cases:
        test_generation_with_parameters(**case)
        # Add a delay between generations to avoid rate limits
        time.sleep(2)

def main() -> None:
    """Main function to run the test script."""
    logger.info("Starting question generator tests")
    
    # Test generation from scratch with increasing max_retries
    test_generation_with_parameters(
        lesson="main_idea",
        difficulty="medium",
        max_retries=0  # No retries, just see initial generation quality
    )
    
    test_generation_with_parameters(
        lesson="main_idea",
        difficulty="medium",
        max_retries=1  # One retry to see improvement
    )
    
    # Test with an example question
    test_with_example()
    
    # Uncomment to run batch generation tests
    # test_batch_generation()
    
    logger.info("Question generator tests completed")

if __name__ == "__main__":
    main() 