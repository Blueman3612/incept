import os
import requests
from requests.adapters import HTTPAdapter, Retry
from dotenv import load_dotenv
from app.services.quality_control import QualityControlService
from app.models.test_harness import TestExample, QualityStatus, QualityCriterion, MutationType, DifficultyLevel

# Example test data
EXAMPLE_DATA = [
    {
        "content": """Read the following passage and answer the question.

The rainforest is home to many different animals. Colorful birds fly through the tall trees. Monkeys swing from branch to branch. Jaguars hunt on the forest floor. All these animals need the rainforest to live and find shelter.

What is the main idea of this passage?

A) The rainforest has tall trees
B) Many different animals live in and depend on the rainforest
C) Jaguars are good hunters
D) Birds are colorful

Correct Answer: B

Explanation for wrong answers:
A) While the passage mentions tall trees, this is just a detail that supports the main idea about animals living in the rainforest.
B) CORRECT - The passage discusses various animals that live in the rainforest and how they depend on it, making this the main idea.
C) This is just one detail about one type of animal in the rainforest, not the main idea.
D) This is a minor detail about one group of animals, not the main focus of the passage.

Solution:
To find the main idea:
1. Read the entire passage carefully
2. Look for the topic that most sentences discuss
3. Notice that most sentences talk about different animals in the rainforest
4. The last sentence ties it all together by stating all these animals need the rainforest
5. Therefore, the main idea is that many different animals live in and depend on the rainforest""",
        "quality_status": "good",
        "quality_criterion": "completeness",
        "mutation_type": "original",
        "lesson": "main_idea",
        "difficulty_level": "medium"
    },
    # Add more example data as needed...
]

def create_session():
    """Create a requests session with retry logic and timeouts"""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retries, pool_maxsize=100, pool_connections=100)
    session.mount('https://', adapter)
    
    # Set default timeouts
    session.timeout = (10, 90)  # (connect timeout, read timeout)
    return session

def seed_test_data(supabase_url: str, headers: dict) -> None:
    """Seed test data into Supabase if table is empty"""
    try:
        session = create_session()
        # Check if we have any test examples
        response = session.get(
            f"{supabase_url}/rest/v1/test_examples?select=count",
            headers=headers
        )
        response.raise_for_status()
        count = response.json()
        
        if not count:  # If table is empty
            print("No test examples found. Seeding example data...")
            for example in EXAMPLE_DATA:
                response = session.post(
                    f"{supabase_url}/rest/v1/test_examples",
                    headers=headers,
                    json=example
                )
                response.raise_for_status()
            print("Successfully seeded test data.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to seed test data: {str(e)}")

def test_qc_system():
    """Test the QC system against our test examples"""
    # Load environment variables
    load_dotenv()
    
    # Initialize HTTP client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials. Please check your .env file.")
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    try:
        session = create_session()
        # First, ensure we have test data
        seed_test_data(supabase_url, headers)
        
        # Get all test examples
        response = session.get(
            f"{supabase_url}/rest/v1/test_examples",
            headers=headers
        )
        response.raise_for_status()
        examples = response.json()
        
        if not examples:
            raise ValueError("No test examples found in database after seeding.")
        
        qc_service = QualityControlService()
        
        print(f"\nTesting QC system against {len(examples)} examples...")
        print("=" * 80)
        
        correct_classifications = 0
        total_evaluated = 0
        
        for example in examples:
            try:
                print(f"\nEvaluating example (ID: {example['id']}):")
                print(f"Expected quality: {example['quality_status']}")
                print(f"Testing criterion: {example['quality_criterion']}")
                print("-" * 40)
                
                # Evaluate the question
                result = qc_service.check_quality(example['content'])
                
                # Check if classification matches expected
                expected_pass = example['quality_status'] == 'good'
                classification_correct = result.passed == expected_pass
                
                if classification_correct:
                    correct_classifications += 1
                    print("✓ Correctly classified!")
                else:
                    print("✗ Incorrectly classified!")
                
                print(f"\nScores by criterion:")
                for criterion, score in result.criterion_scores.items():
                    print(f"- {criterion}: {score:.2f}")
                
                print(f"\nFeedback:")
                print(result.feedback)
                print("=" * 80)
                
                # Update metrics
                qc_service.update_metrics(result)
                total_evaluated += 1
                
            except Exception as e:
                print(f"Error evaluating example {example['id']}: {str(e)}")
                print("Continuing with next example...")
                continue
        
        if total_evaluated == 0:
            print("\nNo examples were successfully evaluated.")
            return
        
        # Calculate precision
        precision = correct_classifications / total_evaluated
        print(f"\nOverall precision: {precision:.2%}")
        
        if precision >= 0.99:
            print("✓ QC system meets the 99% precision requirement!")
        else:
            print("✗ QC system needs improvement to reach 99% precision.")
            
    except Exception as e:
        print(f"Error testing QC system: {str(e)}")
        raise

if __name__ == "__main__":
    test_qc_system() 