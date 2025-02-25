#!/usr/bin/env python
"""
Direct test of OpenAI API key using HTTP requests instead of the OpenAI client.
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables")
    exit(1)

# Print first few characters of key for verification
print(f"API Key: {api_key[:8]}...{api_key[-4:]}")

# Test the API key with a direct HTTP request
try:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Say hello world"}
        ],
        "max_tokens": 10
    }
    
    print("Making direct API request to OpenAI...")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload
    )
    
    # Check if the request was successful
    if response.status_code == 200:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print("✅ API key is valid")
        print(f"Response: {content}")
    else:
        print(f"❌ API request failed with status code: {response.status_code}")
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("Check your API key and try again.") 