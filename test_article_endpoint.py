import requests
import time
import json
from pprint import pprint

def test_article_generation():
    """Test the article generation endpoint."""
    print("Testing article generation endpoint...")
    
    # Test data
    data = {
        "course": "Language",
        "grade_level": 4,
        "lesson": "Main Idea",
        "lesson_description": "Identifying the central message or key point of a text",
        "keywords": ["central message", "key point", "topic sentence"]
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/articles/generate",
            json=data
        )
        
        elapsed = time.time() - start_time
        
        print(f"Status code: {response.status_code}")
        print(f"Completed in {elapsed:.2f} seconds")
        
        if response.status_code == 201:
            result = response.json()
            print("\nGenerated Article:")
            print(f"Title: {result.get('title')}")
            print(f"Quality Score: {result.get('quality_score')}")
            print(f"Key Concepts: {', '.join(result.get('key_concepts', []))}")
            print(f"Examples Count: {len(result.get('examples', []))}")
            
            # Print a preview of the content (first 200 chars)
            content = result.get('content', '')
            print(f"\nContent Preview:\n{content[:200]}...")
        else:
            print("\nError Response:")
            try:
                error_details = response.json()
                pprint(error_details)
            except:
                print(f"Raw response: {response.text}")
    
    except Exception as e:
        print(f"Exception occurred: {str(e)}")

if __name__ == "__main__":
    test_article_generation() 