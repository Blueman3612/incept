#!/usr/bin/env python
"""
One-time script to calculate calibration curves for question grading.
This script grades all good examples in the database and calculates
the adjustment curves for each criterion. The results can be hard-coded
into the QuestionService class.

Additionally, this script updates the metadata of each example with its scores
for easier analysis and review.

Usage:
    python calculate_calibration.py [--sample N] [--no-update-metadata]
    
    --sample N: Process only N random examples instead of all (default: all)
    --no-update-metadata: Don't update metadata in the database
"""

import os
import sys
import json
import asyncio
import random
import argparse
from dotenv import load_dotenv
from tqdm import tqdm

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the question service
from app.services.question_service import QuestionService
from app.schemas.question import QuestionGradeRequest


async def calculate_calibration_curves(sample_size=None, update_metadata=True):
    """
    Calculate and output the calibration curves based on good examples.
    
    Args:
        sample_size: If set, use only this many random examples
        update_metadata: If True, update the metadata of each example
    """
    print("🔍 Calculating calibration curves from good examples...")
    
    # Initialize the service
    service = QuestionService()
    
    # Fetch all good examples with their IDs
    headers = {
        "apikey": service.supabase_key,
        "Authorization": f"Bearer {service.supabase_key}",
        "Content-Type": "application/json"
    }
    
    # First, get count of examples to process
    response = service.session.get(
        f"{service.supabase_url}/rest/v1/test_examples",
        headers=headers,
        params={
            "quality_status": "eq.good",
            "select": "count",
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to fetch example count: {response.status_code}")
        return
    
    total_examples = int(response.json()[0]["count"])
    print(f"Found {total_examples} good examples available")
    
    # Apply sample size limit if specified
    limit_param = {}
    if sample_size and sample_size < total_examples:
        print(f"Using a sample of {sample_size} examples")
        limit_param["limit"] = sample_size
    else:
        sample_size = total_examples  # Use all examples
    
    # Get the examples with all relevant fields
    response = service.session.get(
        f"{service.supabase_url}/rest/v1/test_examples",
        headers=headers,
        params={
            "quality_status": "eq.good",
            "select": "id,content,quality_criterion,lesson,difficulty_level,metadata",
            **limit_param,
            "order": "created_at.desc"  # Get most recent examples first
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to fetch good examples: {response.status_code}")
        return
    
    examples = response.json()
    
    # If we're using a random sample, shuffle the examples
    if sample_size < total_examples:
        random.shuffle(examples)
        examples = examples[:sample_size]
        
    print(f"Processing {len(examples)} examples...")
    
    # Prepare for grading
    criterion_scores = {
        "completeness": [],
        "answer_quality": [],
        "explanation_quality": [],
        "language_quality": []
    }
    
    # Grade each example and collect scores
    metadata_status = "updating" if update_metadata else "without updating"
    print(f"\n📝 Grading examples ({metadata_status} metadata)...")
    
    # Create a log file for individual row reports
    log_file = open("calibration_updates.log", "w")
    log_file.write("Example ID,Criterion,Lesson,Difficulty,Completeness,Answer Quality,Explanation Quality,Language Quality,Status\n")
    
    for i, example in tqdm(enumerate(examples), total=len(examples), desc="Processing examples"):
        example_id = example.get("id")
        content = example.get("content")
        criterion = example.get("quality_criterion", "unknown")
        lesson = example.get("lesson", "unknown")
        difficulty = example.get("difficulty_level", "unknown")
        
        if not content or not example_id:
            print(f"Skipping example {i}: Missing content or ID")
            continue
        
        # Get existing metadata (or initialize empty dict)
        metadata = example.get("metadata", {}) or {}
        
        # Create a request object for grading
        request = QuestionGradeRequest(question=content)
        
        # Temporarily disable calibration curves for this evaluation
        original_curves = service.calibration_curves.copy()
        service.calibration_curves = {k: 0.0 for k in service.calibration_curves}
        
        # Grade the example
        try:
            # Get raw scores without calibration applied
            raw_scores = await service._evaluate_criteria(request.question)
            
            # Store scores in a result structure
            scores = {
                "completeness": round(raw_scores.get("completeness", 0.0), 3),
                "answer_quality": round(raw_scores.get("answer_quality", 0.0), 3),
                "explanation_quality": round(raw_scores.get("explanation_quality", 0.0), 3),
                "language_quality": round(raw_scores.get("language_quality", 0.0), 3)
            }
            
            # Create a short report for this example
            row_status = "OK"
            update_status = "N/A"
            
            # Update metadata if requested
            if update_metadata:
                # Add scores to metadata
                metadata["scores"] = scores
                
                # Update the example in the database
                update_response = service.session.patch(
                    f"{service.supabase_url}/rest/v1/test_examples",
                    headers=headers,
                    json={"metadata": metadata},
                    params={"id": f"eq.{example_id}"}
                )
                
                if update_response.status_code not in (200, 204):
                    row_status = "ERROR"
                    update_status = f"Failed to update: {update_response.status_code}"
                    print(f"Failed to update example {example_id}: {update_response.status_code}")
                else:
                    update_status = "Updated"
            
            # Write row report to log file
            log_file.write(f"{example_id},{criterion},{lesson},{difficulty},{scores['completeness']},{scores['answer_quality']},{scores['explanation_quality']},{scores['language_quality']},{update_status}\n")
            
            # Print a brief report for each row (when not using tqdm)
            report = (
                f"ID: {example_id[:8]}... | "
                f"Criterion: {criterion} | "
                f"Scores: C:{scores['completeness']:.2f} "
                f"A:{scores['answer_quality']:.2f} "
                f"E:{scores['explanation_quality']:.2f} "
                f"L:{scores['language_quality']:.2f} | "
                f"Status: {update_status}"
            )
            # Print without breaking the progress bar
            tqdm.write(report)
            
            # Collect raw scores for each criterion
            for criterion, score in raw_scores.items():
                criterion_scores[criterion].append(score)
                
        except Exception as e:
            error_msg = f"Error grading example {i} (ID: {example_id}): {str(e)}"
            tqdm.write(error_msg)
            log_file.write(f"{example_id},{criterion},{lesson},{difficulty},ERROR,ERROR,ERROR,ERROR,{str(e)}\n")
            continue
        
        # Restore original calibration curves
        service.calibration_curves = original_curves
    
    # Close the log file
    log_file.close()
    print(f"\n✅ Individual row reports saved to calibration_updates.log")
    
    # Calculate average scores for each criterion
    avg_scores = {}
    for criterion, scores in criterion_scores.items():
        if scores:
            avg_scores[criterion] = sum(scores) / len(scores)
        else:
            avg_scores[criterion] = 0.0
    
    # Calculate calibration curves (difference between threshold and average)
    curves = {}
    for criterion, avg_score in avg_scores.items():
        # Only apply positive curves (we don't want to make scores worse)
        curve = max(0.0, service.passing_threshold - avg_score)
        curves[criterion] = round(curve, 3)
    
    print("\n📊 CALIBRATION RESULTS:")
    print("=" * 50)
    for criterion, curve in curves.items():
        print(f"  • {criterion}: +{curve:.3f} (avg score was {avg_scores[criterion]:.3f})")
        
    print("\n📋 COPY-PASTE CODE FOR QUESTION SERVICE:")
    print("=" * 50)
    code = f"""
        # Pre-calculated calibration curves from good examples
        self.calibration_curves = {{
            "completeness": {curves.get('completeness', 0.0):.3f},
            "answer_quality": {curves.get('answer_quality', 0.0):.3f},
            "explanation_quality": {curves.get('explanation_quality', 0.0):.3f},
            "language_quality": {curves.get('language_quality', 0.0):.3f}
        }}
        
        # Mark as already calibrated
        self.is_calibrated = True
    """
    print(code)
    
    # Save to file for reference
    with open("calibration_results.json", "w") as f:
        json.dump({
            "curves": curves,
            "average_scores": avg_scores,
            "sample_size": len(examples),
            "total_examples": total_examples
        }, f, indent=2)
    
    print(f"\n💾 Results saved to calibration_results.json")
    if update_metadata:
        print(f"✅ Metadata updated for {len(examples)} examples")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Calculate calibration curves for question grading')
    parser.add_argument('--sample', type=int, help='Number of examples to sample (default: all)')
    parser.add_argument('--no-update-metadata', action='store_true', help='Skip updating metadata')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Run the calibration
    asyncio.run(calculate_calibration_curves(
        sample_size=args.sample, 
        update_metadata=not args.no_update_metadata
    )) 