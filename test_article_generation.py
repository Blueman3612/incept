import requests
import json

# API endpoint
url = "http://localhost:8000/api/v1/articles/generate-article"

# Request payload
payload = {
    "topic": "Creative Writing: Building Strong Characters",
    "grade_level": 4,
    "subject": "Language Arts",
    "difficulty": "intermediate",
    "keywords": ["character development", "personality traits", "dialogue", "description"],
    "style": "creative"
}

# Headers
headers = {
    "Content-Type": "application/json"
}

try:
    # Make the POST request
    response = requests.post(url, json=payload, headers=headers)
    
    # Check if the request was successful
    response.raise_for_status()
    
    # Print the response in a formatted way
    print("\nGenerated Article:")
    print("=" * 80)
    article = response.json()
    print(f"Article ID: {article['id']}")
    print(f"Title: {article['title']}")
    print("-" * 80)
    print("Content:")
    print(article['content'])
    print("-" * 80)
    print("Key Concepts:")
    for concept in article['key_concepts']:
        print(f"- {concept}")
    print("-" * 80)
    print("Examples:")
    for example in article['examples']:
        print(f"- {example}")
    print("-" * 80)
    print("\nMetadata:")
    print(f"Grade Level: {article['grade_level']}")
    print(f"Subject: {article['subject']}")
    print(f"Difficulty: {article['difficulty_level']}")
    print(f"Created At: {article['created_at']}")
    print(f"Tags: {', '.join(article['tags'])}")
    
except requests.exceptions.RequestException as e:
    print(f"Error making request: {e}")
    if hasattr(e.response, 'text'):
        print(f"Error details: {e.response.text}")
except Exception as e:
    print(f"Unexpected error: {e}") 