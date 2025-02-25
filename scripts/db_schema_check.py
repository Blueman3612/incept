#!/usr/bin/env python
"""
Script to check the database schema and understand insertion requirements.
"""

import os
import json
import requests
from dotenv import load_dotenv

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
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Function to check if a table exists and get its columns
def check_table_schema(table_name):
    print(f"\n🔍 Checking schema for table: {table_name}")
    
    # Get the first example to understand the schema
    response = requests.get(
        f"{supabase_url}/rest/v1/{table_name}",
        headers=headers,
        params={
            "limit": 1
        }
    )
    
    if response.status_code != 200:
        print(f"Error: Failed to access table {table_name}: {response.status_code}")
        return None
    
    examples = response.json()
    if not examples:
        print(f"No examples found in table {table_name}")
        return None
    
    # Print the schema
    example = examples[0]
    print("Fields in the table:")
    for key, value in example.items():
        value_type = type(value).__name__
        if isinstance(value, dict):
            print(f"  - {key} (object): {json.dumps(value, indent=2)}")
        else:
            print(f"  - {key} ({value_type}): {value}")
    
    return example

# Function to try a simple insertion with debug info
def test_insertion(table_name, data):
    print(f"\n🧪 Testing insertion into table: {table_name}")
    print(f"Request URL: {supabase_url}/rest/v1/{table_name}")
    print(f"Headers: {headers}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    response = requests.post(
        f"{supabase_url}/rest/v1/{table_name}",
        headers=headers,
        json=data
    )
    
    status = response.status_code
    print(f"Response status: {status}")
    
    if status not in (200, 201, 204):
        print(f"Error response: {response.text}")
    else:
        print("Insertion successful!")
    
    return status

# Main execution
print("📊 Database Schema Check")

# Check the schema of the test_examples table
example = check_table_schema("test_examples")

if example:
    # Create a minimal test example based on the real one
    test_example = {
        "id": "test-example-123",
        "content": "This is a test example for insertion.",
        "quality_status": "bad",
        "quality_criterion": example.get("quality_criterion", "question_stem"),
        "mutation_type": "test_mutation"
    }
    
    # Add any other required fields from the example
    for key, value in example.items():
        if key not in test_example and key != "id" and not (isinstance(value, dict) and value == {}):
            test_example[key] = value
    
    # Remove any auto-generated fields that might cause issues
    for key in ["created_at", "updated_at"]:
        if key in test_example:
            del test_example[key]
    
    # Test the insertion
    test_insertion("test_examples", test_example) 