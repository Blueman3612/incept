#!/usr/bin/env python
"""
Batch test script for article generation and grading.

This script runs tests on multiple article lessons and compiles the results into CSV and JSON files.
It analyzes quality metrics, performance statistics, and success rates across multiple generated articles.

Usage:
    python scripts/batch_test_articles.py --count 5 --grade 4 --course "Language"
"""

import os
import sys
import json
import time
import random
import logging
import argparse
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add the project root to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.services.article_generator import generate_article_with_grading
except ImportError:
    print("Error: Unable to import required modules from app.")
    print("Make sure you're running this script from the project root.")
    sys.exit(1)

# Sample lessons for Grade 4 Language
SAMPLE_LESSONS = [
    "Main Idea",
    "Supporting Details",
    "Context Clues",
    "Text Structure",
    "Figurative Language",
    "Character Analysis",
    "Setting",
    "Summarizing",
    "Comparing and Contrasting",
    "Making Inferences",
    "Drawing Conclusions",
    "Cause and Effect",
    "Fact vs Opinion",
    "Author's Purpose",
    "Point of View"
]

# Configure logging
log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_directory, exist_ok=True)
log_filename = os.path.join(log_directory, f'batch_test_{log_timestamp}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

def run_batch_tests(
    count: int = 3,
    grade_level: int = 4,
    course: str = "Language",
    lessons: List[str] = None,
    lesson_descriptions: Dict[str, str] = None,
    max_retries: int = 3,
    output_dir: str = "batch_results"
) -> Dict[str, Any]:
    """
    Run batch tests for article generation and grading.
    
    Args:
        count: Number of articles to generate
        grade_level: Target grade level (1-8)
        course: Course name (e.g., "Language", "Math", "Science")
        lessons: List of lesson topics to use (will randomly select from default list if not provided)
        lesson_descriptions: Optional dictionary mapping lessons to their descriptions
        max_retries: Maximum improvement attempts per article
        output_dir: Directory to save results
        
    Returns:
        Dictionary with batch test results and statistics
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Select lessons
    selected_lessons = lessons
    if not selected_lessons:
        # Randomly select 'count' lessons from the sample list
        selected_lessons = random.sample(SAMPLE_LESSONS, min(count, len(SAMPLE_LESSONS)))
        # If we need more lessons than we have samples, repeat some
        if count > len(SAMPLE_LESSONS):
            extra_needed = count - len(SAMPLE_LESSONS)
            selected_lessons += random.choices(SAMPLE_LESSONS, k=extra_needed)
    elif len(selected_lessons) < count:
        # If user provided fewer lessons than count, repeat to reach count
        selected_lessons = (selected_lessons * ((count // len(selected_lessons)) + 1))[:count]
    
    # Initialize counters and variables
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = os.path.join(output_dir, f"batch_results_{timestamp}.csv")
    
    # Start batch test
    logging.info(f"Starting batch test with {count} articles")
    logging.info(f"Grade level: {grade_level}, Course: {course}")
    logging.info(f"Lessons: {selected_lessons}")
    
    # Initialize results counters
    successful_articles = 0
    failed_articles = 0
    total_generation_time = 0
    total_grading_time = 0
    all_results = []
    
    # Create CSV file and write header
    with open(results_file, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow([
            "Lesson", 
            "Grade Level", 
            "Course",
            "Overall Score",
            "Passing",
            "Generation Time (s)",
            "Grading Time (s)",
            "Total Time (s)",
            "Attempts",
            "Critical Issues Count"
        ])
        
        # Process each lesson
        for i, lesson in enumerate(selected_lessons):
            try:
                logging.info(f"\n[{i+1}/{count}] Processing lesson: {lesson}")
                
                # Get lesson description if available
                lesson_description = None
                if lesson_descriptions and lesson in lesson_descriptions:
                    lesson_description = lesson_descriptions[lesson]
                
                # Generate article
                start_time = time.time()
                
                # Set up metadata
                metadata = {}
                
                result = generate_article_with_grading(
                    lesson=lesson,
                    grade_level=grade_level,
                    course=course,
                    lesson_description=lesson_description,
                    metadata=metadata,
                    max_retries=max_retries
                )
                
                # Extract data from result
                article_content = result.get("content", "")
                article_metadata = result.get("metadata", {})
                generation_history = result.get("generation_history", [])
                grade_results = result.get("grade_results", {})
                
                # Calculate times
                total_time = time.time() - start_time
                
                # Estimate generation time (assuming grading takes about 20% of total time)
                generation_time = total_time * 0.8
                grading_time = total_time * 0.2
                
                # Update counters
                if grade_results.get("passing", False):
                    successful_articles += 1
                    logging.info(f"✅ Article PASSED quality checks")
                else:
                    failed_articles += 1
                    logging.info(f"❌ Article FAILED quality checks")
                
                total_generation_time += generation_time
                total_grading_time += grading_time
                
                # Save article to file
                safe_lesson = "".join([c if c.isalnum() else "_" for c in lesson])
                article_filename = os.path.join(output_dir, f"article_{safe_lesson}_{i+1}.md")
                with open(article_filename, 'w', encoding='utf-8') as f:
                    f.write(f"# {lesson} - Grade {grade_level} {course}\n\n")
                    f.write(article_content)
                
                # Save grade results to file
                results_filename = os.path.join(output_dir, f"grade_results_{safe_lesson}_{i+1}.json")
                with open(results_filename, 'w', encoding='utf-8') as f:
                    json.dump(grade_results, f, indent=2)
                
                # Log results summary
                attempts = len(generation_history) + 1 if generation_history else 1
                critical_issues = len(grade_results.get("critical_issues", []))
                
                logging.info(f"Score: {grade_results.get('overall_score', 0):.2f}, Passing: {grade_results.get('passing', False)}")
                logging.info(f"Attempts: {attempts}, Time: {total_time:.2f}s")
                
                # Write to CSV
                csv_writer.writerow([
                    lesson,
                    grade_level,
                    course,
                    grade_results.get("overall_score", 0),
                    grade_results.get("passing", False),
                    f"{generation_time:.2f}",
                    f"{grading_time:.2f}",
                    f"{total_time:.2f}",
                    attempts,
                    critical_issues
                ])
                
                # Add to all results
                result_entry = {
                    "lesson": lesson,
                    "grade_level": grade_level,
                    "course": course,
                    "overall_score": grade_results.get("overall_score", 0),
                    "passing": grade_results.get("passing", False),
                    "generation_time": generation_time,
                    "grading_time": grading_time,
                    "total_time": total_time,
                    "attempts": attempts,
                    "critical_issues_count": critical_issues,
                    "article_filename": article_filename,
                    "results_filename": results_filename
                }
                all_results.append(result_entry)
                
            except Exception as e:
                logging.error(f"Error processing lesson {lesson}: {str(e)}", exc_info=True)
                failed_articles += 1
                
                # Write error to CSV
                csv_writer.writerow([
                    lesson,
                    grade_level,
                    course,
                    0,
                    False,
                    0,
                    0,
                    0,
                    0,
                    0
                ])
    
    # Calculate summary statistics
    success_rate = (successful_articles / count) * 100 if count > 0 else 0
    avg_generation_time = total_generation_time / count if count > 0 else 0
    avg_grading_time = total_grading_time / count if count > 0 else 0
    
    # Calculate scores statistics if we have results
    scores = [r["overall_score"] for r in all_results if "overall_score" in r]
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    
    # Create summary results
    summary = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "count": count,
            "grade_level": grade_level,
            "course": course,
            "max_retries": max_retries
        },
        "results": {
            "total_articles": count,
            "successful_articles": successful_articles,
            "failed_articles": failed_articles,
            "success_rate": f"{success_rate:.2f}%",
            "average_score": avg_score,
            "max_score": max_score,
            "min_score": min_score,
            "average_generation_time": f"{avg_generation_time:.2f}s",
            "average_grading_time": f"{avg_grading_time:.2f}s",
            "total_generation_time": f"{total_generation_time:.2f}s",
            "total_grading_time": f"{total_grading_time:.2f}s",
            "total_time": f"{total_generation_time + total_grading_time:.2f}s"
        },
        "articles": all_results
    }
    
    # Save summary to file
    summary_file = os.path.join(output_dir, f"summary_{timestamp}.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    # Log summary
    logging.info("\n====== BATCH TEST SUMMARY ======")
    logging.info(f"Total articles: {count}")
    logging.info(f"Successful: {successful_articles}, Failed: {failed_articles}")
    logging.info(f"Success rate: {success_rate:.2f}%")
    logging.info(f"Average score: {avg_score:.2f}")
    logging.info(f"Average generation time: {avg_generation_time:.2f}s")
    logging.info(f"Average grading time: {avg_grading_time:.2f}s")
    logging.info(f"Results saved to: {results_file}")
    logging.info(f"Summary saved to: {summary_file}")
    
    return summary

def main():
    parser = argparse.ArgumentParser(description='Run batch tests for article generation and grading')
    
    parser.add_argument('--count', type=int, default=3, help='Number of articles to generate')
    parser.add_argument('--grade', type=int, default=4, choices=range(1, 9), help='Target grade level (1-8)')
    parser.add_argument('--course', type=str, default="Language", help='Course name (e.g., Language, Math, Science)')
    parser.add_argument('--lessons', type=str, help='Comma-separated list of lesson topics (will randomly select if not provided)')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum generation improvement attempts')
    parser.add_argument('--output-dir', type=str, default="batch_results", help='Directory to save results')
    
    args = parser.parse_args()
    
    # Process lessons if provided
    lessons = None
    if args.lessons:
        lessons = [t.strip() for t in args.lessons.split(',') if t.strip()]
    
    try:
        summary = run_batch_tests(
            count=args.count,
            grade_level=args.grade,
            course=args.course,
            lessons=lessons,
            max_retries=args.max_retries,
            output_dir=args.output_dir
        )
        
        # Calculate success rate
        success_rate = summary["results"]["success_rate"]
        
        if "%" in success_rate:
            success_rate = float(success_rate.replace("%", ""))
        
        # Determine exit code based on success rate
        if success_rate >= 75:
            logging.info("Batch test completed successfully with good success rate")
            return 0
        elif success_rate >= 50:
            logging.warning("Batch test completed with moderate success rate")
            return 0
        else:
            logging.error("Batch test completed with low success rate")
            return 1
            
    except Exception as e:
        logging.error(f"Batch test failed: {str(e)}", exc_info=True)
        return 2

if __name__ == "__main__":
    sys.exit(main()) 