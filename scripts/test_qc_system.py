import os
import requests
from dotenv import load_dotenv
from app.services.quality_control import QualityControlService

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
        "Authorization": f"Bearer {supabase_key}"
    }
    
    try:
        # Get all test examples
        response = requests.get(
            f"{supabase_url}/rest/v1/test_examples",
            headers=headers,
            timeout=30.0
        )
        response.raise_for_status()
        examples = response.json()
        
        qc_service = QualityControlService()
        
        print(f"\nTesting QC system against {len(examples)} examples...")
        print("=" * 80)
        
        correct_classifications = 0
        
        for example in examples:
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
        
        # Calculate precision
        precision = correct_classifications / len(examples)
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