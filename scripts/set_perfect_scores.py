#!/usr/bin/env python
"""
Script to set perfect scores (1.0) for all good exemplars in the database.

This is used to establish a "perfect baseline" for our grading system,
explicitly marking all exemplars as perfect rather than trying to
grade them with an imperfect grading system.

Usage:
    python set_perfect_scores.py [--dry-run]
    
    --dry-run: Show what would be updated without making changes
"""

import os
import sys
import json
import asyncio
import argparse
from dotenv import load_dotenv
from tqdm import tqdm

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def set_perfect_scores(dry_run=False):
    """
    Update all good examples in the database to have perfect scores (1.0)
    in their metadata.
    
    Args:
        dry_run: If True, don't actually update the database
    """
    load_dotenv()
    
    # Get Supabase credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: Missing Supabase credentials")
        return
    
    # Set up headers for Supabase API calls
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # Create a session for HTTP requests
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    
    # Get count of good examples
    print("🔍 Counting good examples...")
    response = session.get(
        f"{supabase_url}/rest/v1/test_examples",
        headers=headers,
        params={
            "quality_status": "eq.good",
            "select": "count",
        }
    )
    
    if response.status_code != 200:
        print(f"Error: Failed to fetch example count: {response.status_code}")
        return
    
    total_examples = int(response.json()[0]["count"])
    print(f"Found {total_examples} good examples")
    
    # Get all good examples
    print("📚 Fetching good examples...")
    response = session.get(
        f"{supabase_url}/rest/v1/test_examples",
        headers=headers,
        params={
            "quality_status": "eq.good",
            "select": "id,content,quality_criterion,lesson,difficulty_level,metadata"
        }
    )
    
    if response.status_code != 200:
        print(f"Error: Failed to fetch good examples: {response.status_code}")
        return
    
    examples = response.json()
    
    # Create a log file
    log_file = open("perfect_scores_update.log", "w")
    log_file.write("Example ID,Criterion,Original Scores,Status\n")
    
    # Perfect scores to apply
    perfect_scores = {
        "completeness": 1.0,
        "answer_quality": 1.0,
        "explanation_quality": 1.0,
        "language_quality": 1.0
    }
    
    # Update metadata for each example
    print(f"\n✨ {'Simulating updates' if dry_run else 'Updating'} for {len(examples)} examples...")
    
    updated_count = 0
    for example in tqdm(examples, desc="Processing examples"):
        example_id = example.get("id")
        criterion = example.get("quality_criterion", "unknown")
        
        # Get current metadata
        metadata = example.get("metadata", {}) or {}
        current_scores = metadata.get("scores", {})
        
        # Store original scores for logging
        original_scores = json.dumps(current_scores) if current_scores else "None"
        
        # Update metadata with perfect scores
        metadata["scores"] = perfect_scores
        
        # Log the update
        status = "Would update" if dry_run else "Updating"
        log_file.write(f"{example_id},{criterion},{original_scores},{status}\n")
        
        # Update in database if not dry run
        if not dry_run:
            update_response = session.patch(
                f"{supabase_url}/rest/v1/test_examples",
                headers=headers,
                json={"metadata": metadata},
                params={"id": f"eq.{example_id}"}
            )
            
            if update_response.status_code not in (200, 204):
                status = f"Error: {update_response.status_code}"
                print(f"Failed to update example {example_id}: {update_response.status_code}")
                log_file.write(f"{example_id},{criterion},{original_scores},{status}\n")
            else:
                updated_count += 1
                
                # Print progress report
                report = (
                    f"ID: {example_id[:8]}... | "
                    f"Criterion: {criterion} | "
                    f"Original scores: {original_scores} | "
                    f"Status: Updated to perfect scores"
                )
                tqdm.write(report)
    
    # Close the log file
    log_file.close()
    
    # Print summary
    print(f"\n✅ {'Simulation complete' if dry_run else 'Update complete'}")
    print(f"📝 Details saved to perfect_scores_update.log")
    
    if not dry_run:
        print(f"🎯 Successfully set perfect scores for {updated_count} of {len(examples)} examples")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Set perfect scores for all good exemplars')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    args = parser.parse_args()
    
    # Run the update
    asyncio.run(set_perfect_scores(dry_run=args.dry_run)) 