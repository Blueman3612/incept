#!/usr/bin/env python
"""
Script to generate mutations from good examples to create informative bad examples.

This script takes good examples and creates mutations for each quality criterion,
generating bad examples that can be used to train our grading system.

Usage:
    python generate_mutations.py [--sample N] [--dry-run]
    
    --sample N: Process only N random examples (default: 10)
    --dry-run: Show what would be generated without saving to the database
"""

import os
import sys
import json
import asyncio
import random
import argparse
from uuid import uuid4
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm
import requests

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# The types of mutations we'll create
MUTATION_TYPES = [
    "completeness_mutation",  # Remove required parts (e.g., explanations)
    "answer_quality_mutation",  # Make answers ambiguous or implausible
    "explanation_quality_mutation",  # Make explanations vague or incorrect
    "language_quality_mutation"  # Use inappropriate vocabulary or grammar
]

# OpenAI API for mutations
def generate_mutation(good_example: Dict[str, Any], mutation_type: str) -> str:
    """
    Generate a mutated version of a good example based on the specified mutation type.
    
    Args:
        good_example: The good example to mutate
        mutation_type: The type of mutation to apply
        
    Returns:
        str: The mutated content
    """
    from openai import OpenAI
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Initialize OpenAI client with only the API key
    client = OpenAI(api_key=api_key)
    
    # Get the original content
    content = good_example.get("content", "")
    criterion = good_example.get("quality_criterion", "unknown")
    
    # Create mutation prompts based on mutation type
    if mutation_type == "completeness_mutation":
        prompt = f"""
You are an educational content quality control expert. 
I'll show you a GOOD example of a high quality Grade 4 question.
Create a BAD version that has COMPLETENESS issues by removing one or more of these required components:
- Question stem
- Answer options
- Correct answer indication
- Explanations for wrong answers
- Solution steps

MODIFY the content to be incomplete, but make it subtle - don't make it obvious that parts are missing.

GOOD EXAMPLE:
{content}

BAD EXAMPLE (incomplete):
"""
    
    elif mutation_type == "answer_quality_mutation":
        prompt = f"""
You are an educational content quality control expert. 
I'll show you a GOOD example of a high quality Grade 4 question.
Create a BAD version that has ANSWER QUALITY issues by:
- Making multiple answers potentially correct
- Using implausible or nonsensical distractors
- Making the correct answer stand out obviously
- Making distractors too similar to each other

MODIFY the content to have answer quality issues, but make it subtle.

GOOD EXAMPLE:
{content}

BAD EXAMPLE (poor answer quality):
"""
    
    elif mutation_type == "explanation_quality_mutation":
        prompt = f"""
You are an educational content quality control expert. 
I'll show you a GOOD example of a high quality Grade 4 question.
Create a BAD version that has EXPLANATION QUALITY issues by:
- Using vague or generic explanations for wrong answers
- Providing incorrect explanations
- Removing steps from the solution
- Making explanations less educational

MODIFY the content to have explanation quality issues, but make it subtle.

GOOD EXAMPLE:
{content}

BAD EXAMPLE (poor explanation quality):
"""
    
    elif mutation_type == "language_quality_mutation":
        prompt = f"""
You are an educational content quality control expert. 
I'll show you a GOOD example of a high quality Grade 4 question.
Create a BAD version that has LANGUAGE QUALITY issues by:
- Using vocabulary that's too advanced for Grade 4
- Using complicated sentence structures
- Using ambiguous wording
- Introducing minor grammatical errors
- Using inconsistent terminology

MODIFY the content to have language quality issues, but make it subtle.

GOOD EXAMPLE:
{content}

BAD EXAMPLE (poor language quality):
"""
        
    else:
        # Default fallback prompt
        prompt = f"""
You are an educational content quality control expert. 
I'll show you a GOOD example of a high quality Grade 4 question.
Create a BAD version with quality issues.

GOOD EXAMPLE:
{content}

BAD EXAMPLE:
"""
    
    # Make API call to generate mutation
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an educational content quality control expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
            n=1
        )
        
        mutated_content = response.choices[0].message.content.strip()
        return mutated_content
        
    except Exception as e:
        print(f"Error generating mutation: {str(e)}")
        return None


def create_mutations(sample_size=10, dry_run=False):
    """
    Create mutations from good examples to generate bad examples.
    
    Args:
        sample_size: Number of good examples to sample for mutation
        dry_run: If True, don't save to database
    """
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: Missing Supabase credentials")
        return
    
    # Get OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("Error: Missing OpenAI API key")
        return
    
    # Set up headers for Supabase API calls
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # Get good examples
    print("🔍 Fetching good examples...")
    response = requests.get(
        f"{supabase_url}/rest/v1/test_examples",
        headers=headers,
        params={
            "quality_status": "eq.good",
            "select": "id,content,quality_criterion,lesson,difficulty_level,metadata",
            "limit": sample_size * 2  # Get more than we need to ensure diversity
        }
    )
    
    if response.status_code != 200:
        print(f"Error: Failed to fetch good examples: {response.status_code}")
        return
    
    all_examples = response.json()
    
    # Sample randomly from the examples
    if len(all_examples) > sample_size:
        examples = random.sample(all_examples, sample_size)
    else:
        examples = all_examples
    
    print(f"Found {len(examples)} good examples to mutate")
    
    # Create a log file
    log_file = open("mutations_generated.log", "w")
    log_file.write("Original ID,Mutation Type,New ID,Status\n")
    
    # Generate mutations
    print("\n✨ Generating mutations...")
    
    # Track total mutations
    total_mutations = 0
    created_mutations = 0
    
    for example in tqdm(examples, desc="Processing examples"):
        example_id = example.get("id")
        content = example.get("content")
        criterion = example.get("quality_criterion", "unknown")
        lesson = example.get("lesson", "unknown")
        difficulty = example.get("difficulty_level", "unknown")
        
        if not content or not example_id:
            print(f"Skipping example: Missing content or ID")
            continue
        
        # Create mutations for each mutation type
        for mutation_type in tqdm(MUTATION_TYPES, desc=f"Creating mutations for {example_id[:8]}...", leave=False):
            total_mutations += 1
            
            # Generate the mutation
            try:
                mutated_content = generate_mutation(example, mutation_type)
                
                if not mutated_content:
                    log_file.write(f"{example_id},{mutation_type},N/A,Failed to generate\n")
                    continue
                
                # Create a new bad example with the mutation
                new_id = str(uuid4())
                
                bad_example = {
                    "id": new_id,
                    "content": mutated_content,
                    "quality_status": "bad",
                    "quality_criterion": criterion,
                    "mutation_type": mutation_type,
                    "lesson": lesson,
                    "difficulty_level": difficulty,
                    "metadata": {
                        "original_id": example_id,
                        "mutation_type": mutation_type,
                        "scores": {
                            "completeness": 0.0 if mutation_type == "completeness_mutation" else 1.0,
                            "answer_quality": 0.0 if mutation_type == "answer_quality_mutation" else 1.0,
                            "explanation_quality": 0.0 if mutation_type == "explanation_quality_mutation" else 1.0,
                            "language_quality": 0.0 if mutation_type == "language_quality_mutation" else 1.0
                        }
                    }
                }
                
                # Print the first part of the mutated content for review
                preview = mutated_content[:150] + "..." if len(mutated_content) > 150 else mutated_content
                report = (
                    f"Original ID: {example_id[:8]}... | "
                    f"Mutation: {mutation_type} | "
                    f"New ID: {new_id[:8]}..."
                )
                tqdm.write(report)
                tqdm.write(f"Preview: {preview}")
                tqdm.write("-" * 50)
                
                # Save to database if not a dry run
                if not dry_run:
                    insert_response = requests.post(
                        f"{supabase_url}/rest/v1/test_examples",
                        headers=headers,
                        json=bad_example
                    )
                    
                    if insert_response.status_code not in (200, 201, 204):
                        log_file.write(f"{example_id},{mutation_type},{new_id},Failed to insert: {insert_response.status_code}\n")
                        print(f"Failed to insert mutation: {insert_response.status_code}")
                    else:
                        log_file.write(f"{example_id},{mutation_type},{new_id},Inserted\n")
                        created_mutations += 1
                else:
                    log_file.write(f"{example_id},{mutation_type},{new_id},Would insert (dry run)\n")
                    created_mutations += 1
                
            except Exception as e:
                log_file.write(f"{example_id},{mutation_type},N/A,Error: {str(e)}\n")
                print(f"Error creating mutation: {str(e)}")
    
    # Close the log file
    log_file.close()
    
    # Print summary
    print(f"\n✅ {'Simulation complete' if dry_run else 'Mutation generation complete'}")
    print(f"📝 Details saved to mutations_generated.log")
    print(f"🎯 {'Would create' if dry_run else 'Created'} {created_mutations} of {total_mutations} possible mutations")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate mutations from good examples')
    parser.add_argument('--sample', type=int, default=10, help='Number of good examples to sample (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without saving to the database')
    args = parser.parse_args()
    
    # Run the mutation generator
    create_mutations(sample_size=args.sample, dry_run=args.dry_run) 