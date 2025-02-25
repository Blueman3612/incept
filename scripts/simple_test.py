#!/usr/bin/env python
"""
Minimal test script for OpenAI client without any other imports.
"""

import os

# Get API key directly from environment
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables")
    exit(1)

try:
    from openai import OpenAI
    print("✅ Successfully imported OpenAI")
    
    # Create client with only api_key
    client = OpenAI(api_key=api_key)
    print("✅ Successfully created OpenAI client")
    
    # No API call, just test initialization
    print("✅ Client initialization successful")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print(f"Error type: {type(e)}")
    import traceback
    traceback.print_exc() 