#!/usr/bin/env python
"""
Test script for the article generator and grader.

This script:
1. Generates an article using specified parameters
2. Logs the generation process and results
3. Grades the generated article
4. Provides detailed performance metrics

Usage:
    python scripts/test_article_generator.py --lesson "main_idea" --grade 4 --course "Language" --difficulty easy
"""

import os
import sys
import logging
import argparse
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the project root to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.services.article_generator import generate_article_with_grading
    from app.services.article_grader import grade_article
except ImportError:
    print("Error: Unable to import required modules from app.")
    print("Make sure you're running this script from the project root.")
    sys.exit(1)

# Configure logging
log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_directory, exist_ok=True)
log_filename = os.path.join(log_directory, f'article_test_{log_timestamp}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def log_separator(message: str = None):
    """Print a separator line with an optional message."""
    width = 80
    if message:
        logger.info(f"\n{message.center(width, '=')}\n")
    else:
        logger.info('=' * width)

def log_json(data: Dict[str, Any], title: str = None):
    """Log JSON data in a readable format."""
    if title:
        logger.info(f"\n{title}:")
    logger.info(json.dumps(data, indent=2))

def log_article_content(content: str, title: str = "ARTICLE CONTENT"):
    """Log article content with a title and formatting."""
    log_separator(title)
    # Ensure readable line lengths by wrapping at 100 chars
    logger.info(content)
    log_separator()

def generate_and_grade_article(
    lesson: str,
    grade_level: int,
    course: str,
    keywords: Optional[List[str]] = None,
    lesson_description: Optional[str] = None,
    max_retries: int = 5,
    save_output: bool = True
) -> Dict[str, Any]:
    """
    Generate and grade an article, with detailed logging of the process.
    
    Args:
        lesson: Lesson topic
        grade_level: Target grade level
        course: Course name
        keywords: Optional list of keywords to include
        lesson_description: Optional lesson description
        max_retries: Maximum improvement attempts
        save_output: Whether to save output files
        
    Returns:
        Dictionary with the test results
    """
    # Log test parameters
    log_separator("GENERATION PARAMETERS")
    params = {
        "lesson": lesson,
        "grade_level": grade_level,
        "course": course,
        "keywords": keywords or [],
        "lesson_description": lesson_description or "",
        "max_retries": max_retries
    }
    log_json(params)
    
    # Time the generation
    start_time = time.time()
    
    # Generate article
    try:
        logger.info(f"Generating article on '{lesson}' for Grade {grade_level} {course}...")
        result = generate_article_with_grading(
            lesson=lesson,
            grade_level=grade_level,
            course=course,
            keywords=keywords,
            lesson_description=lesson_description,
            max_retries=max_retries,
            metadata={}  # Add empty metadata dictionary
        )
        
        generation_time = time.time() - start_time
        logger.info(f"Article generation completed in {generation_time:.2f} seconds")
        
        # Extract results
        article_content = result.get("content", "")
        article_title = result.get("title", "Untitled Article")
        generation_metadata = result.get("metadata", {})  # Already using get with default
        grade_results = result.get("grade_results", {})  # Using get with default empty dict
        score = grade_results.get("overall_score", 0.0)  # Already using get with default
        
        # Log article metadata
        log_separator("ARTICLE METADATA")
        log_json(generation_metadata)
        
        # Log article content
        log_separator(f"ARTICLE: {article_title}")
        log_article_content(article_content)
        
        # Log grading results
        log_separator("GRADING RESULTS")
        log_json(grade_results)
        
        # Log feedback
        log_separator("FEEDBACK")
        logger.info(grade_results.get("feedback", "No feedback provided"))
        
        # Save outputs
        if save_output and article_content.strip():
            # Save to output directory
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create safe filename - replace spaces with underscores and remove special chars
            safe_lesson = lesson.replace(" ", "_")
            safe_lesson = "".join([c if c.isalnum() or c == "_" else "" for c in safe_lesson])
            
            # Save article
            article_filename = os.path.join(output_dir, f"article_{safe_lesson}_{grade_level}.md")
            with open(article_filename, 'w', encoding='utf-8') as f:
                f.write(f"# {article_title}\n\n")
                f.write(article_content)
            logger.info(f"Article saved to: {article_filename}")
            
            # Save grade results
            results_filename = os.path.join(output_dir, f"grade_results_{safe_lesson}_{grade_level}.json")
            with open(results_filename, 'w', encoding='utf-8') as f:
                json.dump(grade_results, f, indent=2)
            logger.info(f"Grading results saved to: {results_filename}")
        
        # Log summary
        log_separator("SUMMARY")
        if score >= 0.7:
            logger.info(f"✅ ARTICLE PASSED with score: {score:.2f}")
        else:
            logger.info(f"❌ ARTICLE FAILED with score: {score:.2f}")
        
        logger.info(f"Generation time: {generation_time:.2f}s")
        logger.info(f"Improvement attempts: {generation_metadata.get('improvement_attempts', 0)}")
        
        passing = grade_results.get("passing", False)
        if passing:
            logger.info("Test completed successfully with PASSING article")
        else:
            logger.info("Test completed with FAILING article")
            
        return result
    except Exception as e:
        logger.exception(f"Error in article generation process: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Generate and grade an educational article')
    
    parser.add_argument('--lesson', required=True, help='Lesson topic (e.g., "Main Idea", "Character Analysis")')
    parser.add_argument('--grade', type=int, default=4, choices=range(1, 9), help='Target grade level (1-8)')
    parser.add_argument('--course', default="Language", help='Course name (e.g., Language, Math, Science)')
    parser.add_argument('--keywords', help='Comma-separated list of keywords to include')
    parser.add_argument('--lesson-description', help='Detailed description of the lesson objectives')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum improvement attempts')
    parser.add_argument('--no-save', action='store_true', help='Don\'t save output files')
    
    args = parser.parse_args()
    
    # Process keywords if provided
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]
    
    # Get lesson description if not provided
    lesson_description = args.lesson_description
    if not lesson_description:
        # Try to get the lesson description from the master list
        try:
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            from generate_and_upload_questions import get_lesson_description
            lesson_description = get_lesson_description(args.lesson)
            if lesson_description:
                logger.info(f"Found lesson description: {lesson_description}")
        except (ImportError, Exception) as e:
            logger.warning(f"Could not import lesson descriptions: {str(e)}")
    
    try:
        # Log start of test
        logger.info(f"Starting article generator test for lesson: {args.lesson}")
        logger.info(f"Log file: {log_filename}")
        
        # Generate and grade article
        result = generate_and_grade_article(
            lesson=args.lesson,
            grade_level=args.grade,
            course=args.course,
            keywords=keywords,
            lesson_description=lesson_description,
            max_retries=args.max_retries,
            save_output=not args.no_save
        )
        
        # Exit based on grading results
        if result.get("grade_results", {}).get("passing", False):
            logger.info("Test completed successfully with PASSING article")
            return 0
        else:
            logger.info("Test completed with FAILING article")
            return 1
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return 2

if __name__ == "__main__":
    sys.exit(main()) 