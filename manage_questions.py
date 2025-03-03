import os
import json
from typing import Dict, Any, List
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase setup
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase_secret_key = os.environ.get("SUPABASE_SECRET_KEY")

# Use service key for operations that require elevated permissions
supabase: Client = create_client(supabase_url, supabase_secret_key or supabase_key)

def get_questions_for_lesson(lesson: str) -> List[Dict[str, Any]]:
    """
    Retrieve all questions for a specific lesson from Supabase.
    
    Args:
        lesson: The lesson name to filter by
        
    Returns:
        List of question dictionaries
    """
    print(f"\nFetching questions for lesson: {lesson}")
    
    try:
        # Query Supabase for questions matching the lesson
        result = supabase.table("questions") \
            .select("*") \
            .eq("lesson", lesson) \
            .execute()
        
        if result.data:
            print(f"Found {len(result.data)} questions")
            return result.data
        else:
            print("No questions found for this lesson")
            return []
            
    except Exception as e:
        print(f"Error fetching questions: {str(e)}")
        return []

def display_question(question: Dict[str, Any], index: int) -> None:
    """
    Display a question's details in a formatted way.
    
    Args:
        question: The question data to display
        index: The question number for display purposes
    """
    print(f"\n{'='*80}")
    print(f"Question {index + 1}")
    print(f"{'='*80}")
    
    # Display basic info
    print(f"ID: {question.get('id')}")
    print(f"Status: {question.get('status', 'unknown')}")
    print(f"Difficulty: {question.get('difficulty', 'unknown')}")
    
    # Display stimuli if present
    stimuli = question.get('stimuli')
    if stimuli:
        print("\nSTIMULI:")
        print("-" * 40)
        print(stimuli)
    else:
        print("\nNo stimuli present")
    
    # Display prompt
    print("\nPROMPT:")
    print("-" * 40)
    print(question.get('prompt', 'No prompt available'))
    
    # Display answer choices if present
    answer_choices = question.get('answer_choices', {})
    if answer_choices:
        print("\nANSWER CHOICES:")
        print("-" * 40)
        for choice, text in answer_choices.items():
            star = "*" if choice == question.get('correct_answer') else " "
            print(f"{star}{choice}: {text}")
    else:
        print("\nNo answer choices available")
    
    # Display wrong answer explanations if present
    wrong_answer_explanations = question.get('wrong_answer_explanations', {})
    if wrong_answer_explanations:
        print("\nWRONG ANSWER EXPLANATIONS:")
        print("-" * 40)
        for choice, explanation in wrong_answer_explanations.items():
            print(f"{choice}: {explanation}")
    else:
        print("\nNo wrong answer explanations available")

def update_stimuli(question_id: str, set_null: bool = True) -> bool:
    """
    Update the stimuli field for a question in Supabase.
    
    Args:
        question_id: The ID of the question to update
        set_null: Whether to set the stimuli to NULL (True) or keep it (False)
        
    Returns:
        Boolean indicating success
    """
    try:
        if set_null:
            print(f"\nSetting stimuli to NULL for question {question_id}")
            result = supabase.table("questions") \
                .update({"stimuli": None}) \
                .eq("id", question_id) \
                .execute()
            
            if result.data:
                print("Successfully updated question")
                return True
            else:
                print("No changes made")
                return False
                
    except Exception as e:
        print(f"Error updating question: {str(e)}")
        return False

def main():
    # Set the lesson we want to examine
    lesson = "Capitalization and Punctuation"
    
    print(f"Starting question management for lesson: {lesson}")
    print("=" * 80)
    
    # Get all questions for the lesson
    questions = get_questions_for_lesson(lesson)
    
    if not questions:
        print("No questions found. Exiting.")
        return
    
    # Process each question
    for i, question in enumerate(questions):
        # Display the question details
        display_question(question, i)
        
        # If there's stimuli, ask if we should remove it
        if question.get('stimuli'):
            while True:
                response = input("\nWould you like to remove this stimuli? (y/n/skip): ").lower()
                
                if response in ['y', 'n', 'skip']:
                    if response == 'y':
                        success = update_stimuli(question['id'], True)
                        if success:
                            print("Stimuli removed successfully")
                        else:
                            print("Failed to remove stimuli")
                    elif response == 'skip':
                        print("\nSkipping remaining questions...")
                        return
                    break
                else:
                    print("Please enter 'y' for yes, 'n' for no, or 'skip' to exit")
        
        # Add a blank line for readability
        print("\n")

if __name__ == "__main__":
    main() 