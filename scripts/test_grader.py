#!/usr/bin/env python
"""
Test script for the QualityGrader service.

This script tests the grader against known good and bad examples to evaluate its
accuracy in identifying quality issues across the four quality criteria.

Usage:
    python test_grader.py [--sample N] [--criterion CRITERION] [--verbose]
    
    --sample N: Test on N random examples (default: 5)
    --criterion: Filter examples by quality criterion (e.g., "question_stem")
    --verbose: Show detailed scores and feedback for each example
"""

import os
import sys
import json
import random
import argparse
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv
from tqdm import tqdm
from collections import defaultdict

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our grader service
from app.services.grader_service import grader

# Load environment variables
load_dotenv()

def fetch_examples(quality_status, limit=5, criterion=None):
    """
    Fetch examples from the database.
    
    Args:
        quality_status: 'good' or 'bad'
        limit: Maximum number of examples to fetch
        criterion: Optional quality criterion to filter by
        
    Returns:
        List of example dictionaries
    """
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: Missing Supabase credentials")
        return []
    
    # Set up headers for Supabase API calls
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json"
    }
    
    # Build query parameters
    params = {
        "quality_status": f"eq.{quality_status}",
        "select": "id,content,quality_criterion,lesson,difficulty_level,metadata,mutation_type",
        "limit": limit * 2  # Get more than we need to ensure diversity
    }
    
    if criterion:
        params["quality_criterion"] = f"eq.{criterion}"
    
    # Make the API request
    response = requests.get(
        f"{supabase_url}/rest/v1/test_examples",
        headers=headers,
        params=params
    )
    
    if response.status_code != 200:
        print(f"Error: Failed to fetch examples: {response.status_code}")
        return []
    
    all_examples = response.json()
    
    # Sample randomly if we have more than requested
    if len(all_examples) > limit:
        examples = random.sample(all_examples, limit)
    else:
        examples = all_examples
    
    return examples

def calculate_metrics(results):
    """
    Calculate precision, recall, and F1 score from the test results.
    
    Args:
        results: Dictionary of test results
        
    Returns:
        Dictionary of metrics
    """
    # Count true positives, false positives, true negatives, false negatives
    tp = results["good_pass_count"]
    fp = results["bad_pass_count"]
    tn = results["bad_fail_count"]
    fn = results["good_fail_count"]
    
    # Calculate metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

def test_grader(sample_size=5, criterion=None, verbose=False):
    """
    Test the grader on good and bad examples.
    
    Args:
        sample_size: Number of examples of each type to test
        criterion: Optional quality criterion to filter by
        verbose: Whether to print detailed results
        
    Returns:
        Dictionary of test results and metrics
    """
    print(f"🔍 Testing grader on {sample_size} examples of each type...")
    
    # Fetch examples
    good_examples = fetch_examples("good", sample_size, criterion)
    bad_examples = fetch_examples("bad", sample_size, criterion)
    
    print(f"📝 Found {len(good_examples)} good examples and {len(bad_examples)} bad examples")
    
    # Count results by example type
    results = {
        "good_pass_count": 0,
        "good_fail_count": 0,
        "bad_pass_count": 0,
        "bad_fail_count": 0,
        "good_examples_tested": len(good_examples),
        "bad_examples_tested": len(bad_examples),
        "criterion_results": defaultdict(lambda: {
            "good_pass": 0, "good_fail": 0, 
            "bad_pass": 0, "bad_fail": 0
        })
    }
    
    # Test good examples
    print("\n✨ Testing good examples...")
    for example in tqdm(good_examples):
        example_id = example.get("id", "unknown")[:8]
        criterion = example.get("quality_criterion", "unknown")
        
        # Prepare metadata
        metadata = {
            "grade_level": 4,
            "quality_criterion": criterion
        }
        
        # Grade the content
        grading_result = grader.grade_content(example["content"], metadata)
        
        # Record the result
        passed = grading_result["overall_result"] == "pass"
        if passed:
            results["good_pass_count"] += 1
            results["criterion_results"][criterion]["good_pass"] += 1
        else:
            results["good_fail_count"] += 1
            results["criterion_results"][criterion]["good_fail"] += 1
        
        # Print detailed results if verbose
        if verbose:
            print(f"\nExample {example_id} ({criterion}):")
            print(f"  Overall: {grading_result['overall_result']}")
            print(f"  Scores: {json.dumps(grading_result['scores'], indent=2)}")
            if 'confidence' in grading_result:
                print(f"  Confidence: {grading_result['confidence']}")
            if 'critical_issues' in grading_result and grading_result['critical_issues']:
                print(f"  Critical Issues: {json.dumps(grading_result['critical_issues'], indent=2)}")
            if not passed:
                print(f"  Feedback:")
                for key, value in grading_result["feedback"].items():
                    print(f"    {key}: {value[:100]}..." if len(value) > 100 else f"    {key}: {value}")
    
    # Test bad examples
    print("\n✨ Testing bad examples...")
    for example in tqdm(bad_examples):
        example_id = example.get("id", "unknown")[:8]
        criterion = example.get("quality_criterion", "unknown")
        mutation_type = example.get("mutation_type", "unknown")
        
        # Prepare metadata
        metadata = {
            "grade_level": 4,
            "quality_criterion": criterion,
            "mutation_type": mutation_type
        }
        
        # Grade the content
        grading_result = grader.grade_content(example["content"], metadata)
        
        # Record the result
        passed = grading_result["overall_result"] == "pass"
        if passed:
            results["bad_pass_count"] += 1
            results["criterion_results"][criterion]["bad_pass"] += 1
        else:
            results["bad_fail_count"] += 1
            results["criterion_results"][criterion]["bad_fail"] += 1
        
        # Print detailed results if verbose
        if verbose:
            print(f"\nExample {example_id} ({criterion}, {mutation_type}):")
            print(f"  Overall: {grading_result['overall_result']}")
            print(f"  Scores: {json.dumps(grading_result['scores'], indent=2)}")
            if 'confidence' in grading_result:
                print(f"  Confidence: {grading_result['confidence']}")
            if 'critical_issues' in grading_result and grading_result['critical_issues']:
                print(f"  Critical Issues: {json.dumps(grading_result['critical_issues'], indent=2)}")
            print(f"  Feedback:")
            for key, value in grading_result["feedback"].items():
                print(f"    {key}: {value[:100]}..." if len(value) > 100 else f"    {key}: {value}")
    
    # Calculate metrics
    metrics = calculate_metrics(results)
    results["metrics"] = metrics
    
    # Print summary
    print("\n📊 OVERALL RESULTS:")
    print(f"  Good examples passing: {results['good_pass_count']}/{results['good_examples_tested']} ({results['good_pass_count']/results['good_examples_tested']*100:.1f}%)")
    print(f"  Bad examples failing: {results['bad_fail_count']}/{results['bad_examples_tested']} ({results['bad_fail_count']/results['bad_examples_tested']*100:.1f}%)")
    print(f"  Precision: {metrics['precision']:.3f}")
    print(f"  Recall: {metrics['recall']:.3f}")
    print(f"  F1 Score: {metrics['f1']:.3f}")
    
    # Print criterion-specific results
    print("\n📊 RESULTS BY CRITERION:")
    for criterion, counts in results["criterion_results"].items():
        good_total = counts["good_pass"] + counts["good_fail"]
        bad_total = counts["bad_pass"] + counts["bad_fail"]
        
        if good_total > 0 or bad_total > 0:
            print(f"  {criterion}:")
            if good_total > 0:
                print(f"    Good examples passing: {counts['good_pass']}/{good_total} ({counts['good_pass']/good_total*100:.1f}%)")
            if bad_total > 0:
                print(f"    Bad examples failing: {counts['bad_fail']}/{bad_total} ({counts['bad_fail']/bad_total*100:.1f}%)")
    
    return results

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test the content quality grader')
    parser.add_argument('--sample', type=int, default=5, help='Number of examples of each type to test (default: 5)')
    parser.add_argument('--criterion', type=str, help='Filter examples by quality criterion')
    parser.add_argument('--verbose', action='store_true', help='Show detailed results')
    args = parser.parse_args()
    
    # Run the test
    test_grader(sample_size=args.sample, criterion=args.criterion, verbose=args.verbose) 