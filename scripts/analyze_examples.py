#!/usr/bin/env python
"""
Script to analyze the distribution of examples in the database.
"""

import os
import json
import requests
from dotenv import load_dotenv
from collections import Counter

# Load environment variables
load_dotenv()

# Get Supabase credentials
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("Error: Missing Supabase credentials")
    exit(1)

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
        "select": "id,quality_criterion,lesson,difficulty_level"
    }
)

if response.status_code != 200:
    print(f"Error: Failed to fetch good examples: {response.status_code}")
    exit(1)

examples = response.json()
print(f"Found {len(examples)} good examples")

# Count distributions
criterion_counter = Counter()
lesson_counter = Counter()
difficulty_counter = Counter()

for example in examples:
    criterion = example.get("quality_criterion", "unknown")
    lesson = example.get("lesson", "unknown")
    difficulty = example.get("difficulty_level", "unknown")
    
    criterion_counter[criterion] += 1
    lesson_counter[lesson] += 1
    difficulty_counter[difficulty] += 1

# Print results
print("\n📊 CRITERIA DISTRIBUTION:")
for criterion, count in criterion_counter.most_common():
    print(f"  {criterion}: {count} ({count/len(examples)*100:.1f}%)")

print("\n📚 LESSON DISTRIBUTION (top 10):")
for lesson, count in lesson_counter.most_common(10):
    print(f"  {lesson}: {count} ({count/len(examples)*100:.1f}%)")

print("\n🔄 DIFFICULTY DISTRIBUTION:")
for difficulty, count in difficulty_counter.most_common():
    print(f"  {difficulty}: {count} ({count/len(examples)*100:.1f}%)")

# Get stats on bad examples
print("\n🔍 Fetching bad examples...")
response = requests.get(
    f"{supabase_url}/rest/v1/test_examples",
    headers=headers,
    params={
        "quality_status": "eq.bad",
        "select": "id,quality_criterion,mutation_type"
    }
)

if response.status_code != 200:
    print(f"Error: Failed to fetch bad examples: {response.status_code}")
    exit(1)

bad_examples = response.json()
print(f"Found {len(bad_examples)} bad examples")

# Count distributions for bad examples
bad_criterion_counter = Counter()
mutation_counter = Counter()

for example in bad_examples:
    criterion = example.get("quality_criterion", "unknown")
    mutation = example.get("mutation_type", "unknown")
    
    bad_criterion_counter[criterion] += 1
    mutation_counter[mutation] += 1

if bad_examples:
    print("\n📊 BAD EXAMPLES BY CRITERIA:")
    for criterion, count in bad_criterion_counter.most_common():
        print(f"  {criterion}: {count} ({count/len(bad_examples)*100:.1f}%)")

    print("\n🔄 MUTATION TYPE DISTRIBUTION:")
    for mutation, count in mutation_counter.most_common():
        print(f"  {mutation}: {count} ({count/len(bad_examples)*100:.1f}%)")

print("\n✅ Analysis complete") 