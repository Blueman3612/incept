#!/usr/bin/env python
"""
Simple test script to verify OpenAI API client configuration.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables")
    exit(1)

# Create client with minimal configuration
try:
    client = OpenAI(api_key=api_key)
    print("✅ Successfully created OpenAI client")
    
    # Test a simple API call
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Say hello world"}
        ],
        max_tokens=10
    )
    
    print("✅ API call successful")
    print(f"Response: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("Check your environment configuration and try again.") 