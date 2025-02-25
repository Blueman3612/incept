#!/usr/bin/env python
"""
Script to generate mutations from good examples to create informative bad examples.

This script takes good examples and creates mutations for each quality criterion,
generating bad examples that can be used to train our grading system.

Usage:
    python generate_mutations_fixed.py [--sample N] [--dry-run] [--exclude-mutated]
    
    --sample N: Process only N random examples (default: 10)
    --dry-run: Show what would be generated without saving to the database
    --exclude-mutated: Exclude examples that have already been used for mutations
"""

import os
import sys
import json
import random
import argparse
import requests
from uuid import uuid4
from typing import List, Dict, Any
from dotenv import load_dotenv
from tqdm import tqdm

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# The types of mutations we'll create and their mapping to database enum values
MUTATION_TYPES = [
    "completeness_mutation",  # Remove required parts (e.g., explanations)
    "answer_quality_mutation",  # Make answers ambiguous or implausible
    "explanation_quality_mutation",  # Make explanations vague or incorrect
    "language_quality_mutation"  # Use inappropriate vocabulary or grammar
]

# Mapping our mutation types to database enum values
MUTATION_TYPE_MAPPING = {
    "completeness_mutation": "stem_mutation",  # Missing parts maps to stem_mutation
    "answer_quality_mutation": "distractor_mutation",  # Poor answer quality maps to distractor_mutation
    "explanation_quality_mutation": "answer_mutation",  # Poor explanations maps to answer_mutation
    "language_quality_mutation": "grammar_mutation"  # Poor language maps to grammar_mutation
}

# Mapping mutations to quality criterion values
CRITERION_MAPPING = {
    "completeness_mutation": "question_stem",  # Completeness issues primarily affect the question stem
    "answer_quality_mutation": "distractors",  # Answer quality issues affect the distractor options
    "explanation_quality_mutation": "correct_answer",  # Explanation issues affect the answer explanation
    "language_quality_mutation": "grammar"  # Language issues map to grammar criterion
}

# OpenAI API for mutations using direct HTTP request
def generate_mutation(good_example: Dict[str, Any], mutation_type: str) -> str:
    """
    Generate a mutated version of a good example based on the specified mutation type.
    
    Args:
        good_example: The good example to mutate
        mutation_type: The type of mutation to apply
        
    Returns:
        str: The mutated content
    """
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
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
    
    # Make API call using direct HTTP request
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": "gpt-4",
            "messages": [
                {"role": "system", "content": "You are an educational content quality control expert."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            mutated_content = result["choices"][0]["message"]["content"].strip()
            return mutated_content
        else:
            print(f"Error in API request: {response.status_code}")
            print(f"Error detail: {response.text}")
            return None
        
    except Exception as e:
        print(f"Error generating mutation: {str(e)}")
        return None


def create_mutations(sample_size=10, dry_run=False, exclude_mutated=False):
    """
    Create mutations from good examples to generate bad examples.
    
    Args:
        sample_size: Number of good examples to sample for mutation
        dry_run: If True, don't save to database
        exclude_mutated: If True, exclude examples that have already been used for mutations
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
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    # Get good examples
    print("🔍 Fetching good examples...")
    
    # If exclude_mutated is True, we need to get the list of already mutated examples
    mutated_original_ids = []
    if exclude_mutated:
        # Fetch the IDs of original examples that have already been mutated
        mutated_response = requests.get(
            f"{supabase_url}/rest/v1/test_examples",
            headers=headers,
            params={
                "quality_status": "eq.bad",
                "select": "id,metadata"  # Get the full metadata object
            }
        )
        
        if mutated_response.status_code == 200:
            # Extract the original IDs from the metadata
            bad_examples = mutated_response.json()
            print(f"Found {len(bad_examples)} bad examples in database")
            
            for item in bad_examples:
                metadata = item.get("metadata", {})
                if isinstance(metadata, dict):
                    original_id = metadata.get("original_id")
                    if original_id and original_id not in mutated_original_ids:
                        mutated_original_ids.append(original_id)
            
            print(f"Found {len(mutated_original_ids)} already mutated examples to exclude")
    
    # Get good examples, excluding those that have already been mutated if requested
    query_params = {
        "quality_status": "eq.good",
        "select": "id,content,quality_criterion,lesson,difficulty_level,metadata",
        "limit": sample_size * 2  # Get more than we need to ensure diversity
    }
    
    response = requests.get(
        f"{supabase_url}/rest/v1/test_examples",
        headers=headers,
        params=query_params
    )
    
    if response.status_code != 200:
        print(f"Error: Failed to fetch good examples: {response.status_code}")
        return
    
    all_examples = response.json()
    
    # If we're excluding mutated examples, filter them out
    if exclude_mutated and mutated_original_ids:
        filtered_examples = []
        excluded_count = 0
        
        for example in all_examples:
            example_id = example.get("id")
            if example_id in mutated_original_ids:
                excluded_count += 1
            else:
                filtered_examples.append(example)
        
        print(f"Excluded {excluded_count} previously mutated examples, {len(filtered_examples)} good examples remain")
        all_examples = filtered_examples
    
    # Sample randomly from the examples
    if len(all_examples) > sample_size:
        examples = random.sample(all_examples, sample_size)
    else:
        examples = all_examples
    
    print(f"Found {len(examples)} good examples to mutate")
    
    # Create a log file
    log_file = open("mutations_generated.log", "w")
    log_file.write("Original ID,Mutation Type,New ID,Status\n")
    
    # Track mutation distributions
    criterion_counter = {}
    mutation_counter = {}
    
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
                
                # Create a new bad example with the mutation - ensure UUID is in correct format
                new_id = str(uuid4())
                
                # Map our mutation type to database enum value
                db_mutation_type = MUTATION_TYPE_MAPPING.get(mutation_type, "stem_mutation")
                
                # Map to appropriate quality criterion based on mutation type
                quality_criterion = CRITERION_MAPPING.get(mutation_type, criterion)
                
                bad_example = {
                    "id": new_id,
                    "content": mutated_content,
                    "quality_status": "bad",
                    "quality_criterion": quality_criterion,
                    "mutation_type": db_mutation_type,
                    "lesson": lesson,
                    "difficulty_level": difficulty,
                    "metadata": {
                        "original_id": example_id,
                        "original_criterion": criterion,
                        "internal_mutation_type": mutation_type,
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
                    f"Mutation: {mutation_type} (DB: {db_mutation_type}) | "
                    f"Criterion: {quality_criterion} | "
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
                        print(f"Error details: {insert_response.text}")
                    else:
                        log_file.write(f"{example_id},{mutation_type},{new_id},Inserted\n")
                        created_mutations += 1
                        
                        # Track distributions for successful inserts
                        criterion_counter[quality_criterion] = criterion_counter.get(quality_criterion, 0) + 1
                        mutation_counter[db_mutation_type] = mutation_counter.get(db_mutation_type, 0) + 1
                else:
                    log_file.write(f"{example_id},{mutation_type},{new_id},Would insert (dry run)\n")
                    created_mutations += 1
                    
                    # Track distributions for dry runs too
                    criterion_counter[quality_criterion] = criterion_counter.get(quality_criterion, 0) + 1
                    mutation_counter[db_mutation_type] = mutation_counter.get(db_mutation_type, 0) + 1
                
            except Exception as e:
                log_file.write(f"{example_id},{mutation_type},N/A,Error: {str(e)}\n")
                print(f"Error creating mutation: {str(e)}")
    
    # Close the log file
    log_file.close()
    
    # Print summary
    print(f"\n✅ {'Simulation complete' if dry_run else 'Mutation generation complete'}")
    print(f"📝 Details saved to mutations_generated.log")
    print(f"🎯 {'Would create' if dry_run else 'Created'} {created_mutations} of {total_mutations} possible mutations")
    
    # Print distribution information
    print("\n📊 MUTATION DISTRIBUTION:")
    for mutation_type, count in mutation_counter.items():
        print(f"  {mutation_type}: {count} ({count/created_mutations*100:.1f}%)")
    
    print("\n📊 QUALITY CRITERION DISTRIBUTION:")
    for criterion, count in criterion_counter.items():
        print(f"  {criterion}: {count} ({count/created_mutations*100:.1f}%)")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate mutations from good examples')
    parser.add_argument('--sample', type=int, default=10, help='Number of good examples to sample (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be generated without saving to the database')
    parser.add_argument('--exclude-mutated', action='store_true', help='Exclude examples that have already been used for mutations')
    args = parser.parse_args()
    
    # Run the mutation generator
    create_mutations(sample_size=args.sample, dry_run=args.dry_run, exclude_mutated=args.exclude_mutated) 