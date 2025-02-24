import os
from dotenv import load_dotenv
from app.services.quality_control import QualityControlService
from app.models.test_harness import TestExample, QualityStatus, QualityCriterion, MutationType, DifficultyLevel
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time

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
    session.timeout = (10, 90)
    return session

def save_example(session, supabase_url: str, headers: dict, example: dict) -> None:
    """Save a test example to Supabase"""
    try:
        response = session.post(
            f"{supabase_url}/rest/v1/test_examples",
            headers=headers,
            json=example
        )
        response.raise_for_status()
        print(f"Saved example with quality_status: {example['quality_status']}")
    except Exception as e:
        print(f"Error saving example: {str(e)}")

def generate_question(qc_service: QualityControlService, lesson: str, difficulty: str) -> str:
    """Generate a new question using GPT-4"""
    prompt = f"""Generate a Grade 4 Language Arts question for the lesson on "{lesson}" at {difficulty} difficulty level.
    The question should:
    1. Include a short passage (2-4 sentences)
    2. Ask about the main idea or key details
    3. Have 4 multiple choice options (A, B, C, D)
    4. Include explanations for wrong answers
    5. Provide a step-by-step solution
    6. Use grade-appropriate vocabulary
    7. Have clear and unambiguous wording
    
    Format the question exactly like this example:
    Read the following passage and answer the question.
    
    [Your 2-4 sentence passage here]
    
    [Your question here]
    
    A) [First option]
    B) [Second option]
    C) [Third option]
    D) [Fourth option]
    
    Correct Answer: [Letter]
    
    Explanation for wrong answers:
    A) [Explanation why A is wrong - skip if A is correct]
    B) [Explanation why B is wrong - skip if B is correct]
    C) [Explanation why C is wrong - skip if C is correct]
    D) [Explanation why D is wrong - skip if D is correct]
    
    Solution:
    [Step-by-step guidance on how to solve this question]"""

    return qc_service._generate_with_gpt(prompt)

def main():
    """Generate and test questions, building our test harness"""
    load_dotenv()
    
    # Initialize services
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")
    
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    session = create_session()
    qc_service = QualityControlService()
    
    # Define our test matrix
    lessons = ["main_idea", "supporting_details", "authors_purpose"]
    difficulties = ["easy", "medium", "hard"]
    target_per_combination = 5  # Number of good examples to generate per lesson/difficulty combo
    
    total_generated = 0
    total_passed = 0
    
    try:
        for lesson in lessons:
            for difficulty in difficulties:
                print(f"\nGenerating questions for lesson: {lesson}, difficulty: {difficulty}")
                print("=" * 80)
                
                good_examples = 0
                attempts = 0
                max_attempts = 20  # Maximum attempts per combination
                
                while good_examples < target_per_combination and attempts < max_attempts:
                    attempts += 1
                    total_generated += 1
                    
                    print(f"\nAttempt {attempts}/{max_attempts} (Good examples: {good_examples}/{target_per_combination})")
                    
                    try:
                        # Generate a question
                        content = generate_question(qc_service, lesson, difficulty)
                        print("\nGenerated question:")
                        print("-" * 40)
                        print(content)
                        print("-" * 40)
                        
                        # Check its quality
                        print("\nChecking quality...")
                        result = qc_service.check_quality(content)
                        
                        # Save the example
                        example = {
                            "content": content,
                            "quality_status": QualityStatus.GOOD if result.passed else QualityStatus.BAD,
                            "quality_criterion": QualityCriterion.COMPLETENESS,  # Default to completeness for generated
                            "mutation_type": MutationType.ORIGINAL,
                            "lesson": lesson,
                            "difficulty_level": difficulty,
                            "metadata": {
                                "scores": result.criterion_scores,
                                "failed_criteria": result.failed_criteria,
                                "feedback": result.feedback
                            }
                        }
                        
                        save_example(session, supabase_url, headers, example)
                        
                        if result.passed:
                            good_examples += 1
                            total_passed += 1
                            print("✓ Question passed quality check!")
                            
                            # Generate mutations from good examples
                            print("\nGenerating mutations...")
                            mutations = qc_service.generate_mutations(TestExample(**example))
                            for mutation in mutations:
                                mutation_dict = mutation.dict()
                                mutation_dict.pop('id', None)  # Remove id as it will be generated by Supabase
                                save_example(session, supabase_url, headers, mutation_dict)
                        else:
                            print("✗ Question failed quality check")
                            print("\nFailed criteria:", ", ".join(result.failed_criteria))
                            print("\nFeedback:")
                            print(result.feedback)
                        
                        # Avoid rate limits
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"Error in generation/testing loop: {str(e)}")
                        continue
                
                print(f"\nCompleted {lesson} {difficulty}: {good_examples}/{target_per_combination} good examples")
        
        # Print final statistics
        print("\nGeneration complete!")
        print(f"Total questions generated: {total_generated}")
        print(f"Questions that passed QC: {total_passed}")
        print(f"Success rate: {(total_passed/total_generated)*100:.2f}%")
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main() 