import requests
import json
import time

# API endpoint URL
BASE_URL = "http://localhost:8000/api/v1"
GENERATE_ENDPOINT = f"{BASE_URL}/articles/generate"
GRADE_ENDPOINT = f"{BASE_URL}/articles/grade"

def test_article_generation():
    """Test the article generation endpoint"""
    
    # Define request payload
    payload = {
        "course": "Language",
        "grade_level": 4,
        "lesson": "Main Idea",
        "lesson_description": "Identifying the central message or key point of a text",
        "keywords": ["central message", "key point", "topic sentence"],
        "style": "standard"
    }
    
    print("Testing article generation endpoint...")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    # Send POST request
    start_time = time.time()
    response = requests.post(GENERATE_ENDPOINT, json=payload)
    end_time = time.time()
    
    # Check response
    if response.status_code == 201:
        article = response.json()
        print(f"\nArticle generated successfully in {end_time - start_time:.2f} seconds!")
        print(f"Title: {article.get('title')}")
        print(f"Quality Score: {article.get('quality_score')}")
        
        # Print excerpt of content
        content = article.get('content', '')
        excerpt = content[:200] + "..." if len(content) > 200 else content
        print(f"\nExcerpt: {excerpt}")
        
        # Save the article to a file
        with open("generated_article.md", "w", encoding="utf-8") as f:
            f.write(f"# {article.get('title')}\n\n")
            f.write(content)
        print("\nFull article saved to 'generated_article.md'")
        
    else:
        print(f"Error: {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error detail: {error_data.get('detail', 'No detail provided')}")
        except:
            print(response.text)

def test_article_grading():
    """Test the article grading endpoint"""
    
    # Read the article content from a file (if available)
    try:
        with open("generated_article.md", "r", encoding="utf-8") as f:
            # Skip the title line
            f.readline()
            f.readline()
            content = f.read()
    except FileNotFoundError:
        # Use a sample article if file doesn't exist
        content = """
        # Understanding Main Ideas
        
        The main idea is the central point or key concept of a text. It tells what the text is mostly about.
        
        ## What is a Main Idea?
        The main idea is the most important thought about the topic. It is what the author wants you to know about the subject.
        
        ### Examples:
        1. **Easy Example**: Read the sentence: "Dogs make great pets because they are loyal and friendly."
           - The main idea is that dogs make great pets.
           
        2. **Medium Example**: Read the paragraph: "The playground was filled with children. Some were swinging on the swings, while others were sliding down the slide. A few children were playing tag, running and laughing."
           - The main idea is that children were playing at the playground.
           
        3. **Hard Example**: Read the short story: "Maria studied all weekend for her science test. She read her textbook twice and made flashcards. She quizzed herself until she knew all the material. On Monday, Maria felt confident and earned an A on her test."
           - The main idea is that Maria's hard work studying led to success on her test.
        """
    
    # Define request payload
    payload = {
        "content": content,
        "metadata": {
            "grade_level": 4,
            "course": "Language",
            "lesson": "Main Idea"
        }
    }
    
    print("\nTesting article grading endpoint...")
    
    # Send POST request
    start_time = time.time()
    response = requests.post(GRADE_ENDPOINT, json=payload)
    end_time = time.time()
    
    # Check response
    if response.status_code == 200:
        result = response.json()
        print(f"Article graded successfully in {end_time - start_time:.2f} seconds!")
        print(f"Overall Score: {result.get('overall_score')}")
        print(f"Passing: {result.get('passing')}")
        
        # Print criterion scores
        print("\nCriterion Scores:")
        for criterion, score in result.get('criterion_scores', {}).items():
            print(f"- {criterion}: {score:.2f}")
        
        # Print feedback excerpt
        feedback = result.get('feedback', '')
        excerpt = feedback[:200] + "..." if len(feedback) > 200 else feedback
        print(f"\nFeedback Excerpt: {excerpt}")
        
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Test article generation
    test_article_generation()
    
    # Test article grading
    test_article_grading() 