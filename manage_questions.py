import os
import json
from typing import Dict, Any, List, Optional, Tuple
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

def analyze_question_context(question: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Analyze a question in context of its stimuli, prompt, and answer choices to suggest edits.
    
    Args:
        question: The question data to analyze
        
    Returns:
        Tuple of (suggestion message, suggested edits) or None if no edits needed
    """
    stimuli = question.get('stimuli', '')
    prompt = question.get('prompt', '')
    answer_choices = question.get('answer_choices', {})
    correct_answer = question.get('correct_answer', '')
    wrong_answer_explanations = question.get('wrong_answer_explanations', {})
    
    # Initialize suggested edits and issues
    suggested_edits = {}
    issues = []
    
    # Check if this is a question about capitalization/punctuation
    is_cap_punct_question = any(term in prompt.lower() for term in 
        ['capital', 'punctuation', 'period', 'comma', 'apostrophe', 'quotation', 'uppercase', 'lowercase'])
        
    # Determine if we're looking for incorrect examples
    looking_for_incorrect = any(term in prompt.lower() for term in [
        # Direct incorrect indicators
        'incorrect', 'wrong', 'improper', 'error', 'mistake', 'fix',
        # Negative forms
        'does not follow', 'do not follow',
        'does not meet', 'do not meet',
        'does not use', 'do not use',
        'does not have', 'do not have',
        'is not', 'are not',
        # Adverb negations
        'not correctly', 'not properly', 'not accurately',
        'incorrectly', 'improperly', 'inaccurately',
        # Needs correction phrases
        'needs correction', 'need correction', 'needs a correction',
        'needs to be corrected', 'need to be corrected', 'should be corrected',
        'requires correction', 'require correction',
        # Specific correction needs
        'needs capitalization', 'needs punctuation',
        'need capitalization', 'need punctuation',
        'needs proper capitalization', 'needs proper punctuation',
        # Combined correction needs
        'needs capitalization and punctuation',
        'needs punctuation and capitalization',
        'need capitalization and punctuation',
        'need punctuation and capitalization',
        # Correction variations
        'correction needed', 'corrections needed',
        'correction required', 'corrections required',
        'requires correcting', 'require correcting',
        'needs correcting', 'need correcting',
        'should be fixed', 'must be fixed',
        'has an error', 'contains an error',
        'has errors', 'contains errors'
    ])
    
    # Check if question is asking for a single example
    asking_for_single = any(term in prompt.lower() for term in [
        'which sentence', 'what sentence', 'find the sentence',
        'identify the sentence', 'select the sentence'
    ])
    
    # For questions asking to identify incorrect examples, the correct answer should have errors
    # and wrong answers should be properly formatted
    if is_cap_punct_question and looking_for_incorrect:
        # Skip format checking for the correct answer - it should have errors
        pass
    
    def normalize_text(text: str) -> str:
        """Normalize text for comparison by removing quotes and extra whitespace"""
        text = text.strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        return text.strip()
    
    def split_into_sentences(text: str) -> List[str]:
        """Split text into sentences, preserving original formatting"""
        sentences = []
        current = ""
        for char in text:
            current += char
            if char in ['.', '!', '?'] and current.strip():
                sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())
        return sentences
    
    # Split stimuli into sentences
    stimuli_sentences = split_into_sentences(stimuli)
    
    # If asking for a single example, check stimuli for consistency
    if asking_for_single and is_cap_punct_question:
        # Count formatting errors in stimuli
        error_count = 0
        for sentence in stimuli_sentences:
            if not (sentence[0].isupper() and sentence.endswith(('.', '!', '?'))):
                error_count += 1
        
        # For questions looking for incorrect examples
        if looking_for_incorrect and error_count != 1:
            issues.append(f"The stimuli contains {error_count} sentences with formatting errors, but the question asks for a single incorrect sentence.")
            # Create corrected stimuli with exactly one error
            corrected_sentences = []
            error_added = False
            for i, sentence in enumerate(stimuli_sentences):
                if i == 0 and not error_added:
                    # Keep the first sentence incorrect if it already is
                    if not (sentence[0].isupper() and sentence.endswith(('.', '!', '?'))):
                        corrected_sentences.append(sentence)
                        error_added = True
                    else:
                        # Make the first sentence incorrect
                        corrected_sentences.append(sentence[0].lower() + sentence[1:].rstrip('.!?'))
                        error_added = True
                else:
                    # Fix all other sentences
                    fixed = sentence[0].upper() + sentence[1:]
                    if not fixed.endswith(('.', '!', '?')):
                        fixed += "."
                    corrected_sentences.append(fixed)
            suggested_edits['stimuli'] = " ".join(corrected_sentences)
        
        # For questions looking for correct examples
        elif not looking_for_incorrect and error_count != len(stimuli_sentences) - 1:
            issues.append(f"The stimuli contains {error_count} sentences with formatting errors, but the question asks for a single correct sentence.")
            # Create corrected stimuli with all but one sentence having errors
            corrected_sentences = []
            correct_added = False
            for i, sentence in enumerate(stimuli_sentences):
                if i == 0 and not correct_added:
                    # Make first sentence correct
                    fixed = sentence[0].upper() + sentence[1:]
                    if not fixed.endswith(('.', '!', '?')):
                        fixed += "."
                    corrected_sentences.append(fixed)
                    correct_added = True
                else:
                    # Make all other sentences incorrect
                    incorrect = sentence[0].lower() + sentence[1:].rstrip('.!?')
                    corrected_sentences.append(incorrect)
            suggested_edits['stimuli'] = " ".join(corrected_sentences)
    
    # Process answer choices
    for letter, text in answer_choices.items():
        normalized_text = normalize_text(text)
        is_quoted = text != normalized_text
        
        # Skip empty answers
        if not normalized_text:
            issues.append(f"Answer choice {letter} is empty or contains only whitespace.")
            continue
            
        # For capitalization/punctuation questions
        if is_cap_punct_question:
            is_properly_formatted = normalized_text[0].isupper() and normalized_text.endswith(('.', '!', '?'))
            
            if looking_for_incorrect:
                # If looking for incorrect examples:
                # - The correct answer should have formatting errors
                # - Wrong answers should be properly formatted
                if letter != correct_answer and not is_properly_formatted:
                    issues.append(f"Wrong answer (choice {letter}) should be properly formatted since we're looking for incorrect examples.")
                    new_text = normalized_text[0].upper() + normalized_text[1:]
                    if not new_text.endswith(('.', '!', '?')):
                        new_text += "."
                    suggested_edits[f'answer_choice_{letter}'] = f'"{new_text}"' if is_quoted else new_text
            else:
                # If looking for correct examples:
                # - The correct answer should be properly formatted
                # - Wrong answers should have formatting errors
                if letter == correct_answer and not is_properly_formatted:
                    issues.append(f"Correct answer (choice {letter}) should be properly formatted since we're looking for correct examples.")
                    new_text = normalized_text[0].upper() + normalized_text[1:]
                    if not new_text.endswith(('.', '!', '?')):
                        new_text += "."
                    suggested_edits[f'answer_choice_{letter}'] = f'"{new_text}"' if is_quoted else new_text
                elif letter != correct_answer and is_properly_formatted:
                    issues.append(f"Wrong answer (choice {letter}) should have formatting errors since we're looking for correct examples.")
                    new_text = normalized_text[0].lower() + normalized_text[1:].rstrip('.!?')
                    suggested_edits[f'answer_choice_{letter}'] = f'"{new_text}"' if is_quoted else new_text
        else:
            # For non-capitalization questions, all answers should be properly formatted
            if not normalized_text[0].isupper():
                issues.append(f"Answer choice {letter} doesn't start with a capital letter.")
                new_text = normalized_text[0].upper() + normalized_text[1:]
                suggested_edits[f'answer_choice_{letter}'] = f'"{new_text}"' if is_quoted else new_text
            
            if not normalized_text.endswith(('.', '!', '?')):
                issues.append(f"Answer choice {letter} doesn't end with proper punctuation.")
                new_text = normalized_text.rstrip() + "."
                suggested_edits[f'answer_choice_{letter}'] = f'"{new_text}"' if is_quoted else new_text
    
    # Check for quoted text in prompt matching stimuli
    if stimuli:
        quoted_texts = []
        current = ""
        in_quote = False
        for char in prompt:
            if char in ['"', '"', '"', "'"]:
                if in_quote:
                    if current:
                        quoted_texts.append(current)
                    current = ""
                in_quote = not in_quote
            elif in_quote:
                current += char
        
        for quoted_text in quoted_texts:
            quoted_text = normalize_text(quoted_text)
            if quoted_text and quoted_text not in stimuli:
                issues.append(f"Quoted text '{quoted_text}' from prompt not found in stimuli.")
    
    # Check for consistency in wrong answer explanations
    for letter in answer_choices:
        if letter != correct_answer and letter not in wrong_answer_explanations:
            issues.append(f"Missing wrong answer explanation for choice {letter}.")
    
    # Check if all answer choices are consistently formatted
    all_correct = all(normalize_text(text)[0].isupper() and normalize_text(text).endswith(('.', '!', '?')) 
                     for text in answer_choices.values())
    all_incorrect = all(not (normalize_text(text)[0].isupper() and normalize_text(text).endswith(('.', '!', '?')))
                       for text in answer_choices.values())
    
    if all_correct and is_cap_punct_question and looking_for_incorrect:
        issues.append("All answer choices are correctly formatted, but we're looking for incorrect examples.")
    
    if all_incorrect and is_cap_punct_question and not looking_for_incorrect:
        issues.append("All answer choices have formatting errors, but we're looking for correct examples.")
    
    # If we found issues, return them with suggested edits
    if issues:
        message = "\n".join(f"- {issue}" for issue in sorted(set(issues)))  # Remove duplicates
        suggested_edits['reason'] = message
        return message, suggested_edits
    
    return None

def display_suggested_edits(message: str, suggested_edits: Dict[str, Any]) -> None:
    """
    Display suggested edits in a clear, formatted way.
    
    Args:
        message: The issue message
        suggested_edits: Dictionary of suggested edits
    """
    print("\nSUGGESTED EDIT:")
    print("-" * 40)
    print("ISSUES FOUND:")
    print(message)
    print("\nSUGGESTED CHANGES:")
    for key, value in suggested_edits.items():
        if key != 'reason':
            if key.startswith('answer_choice_'):
                print(f"Change answer choice {key[-1]} to: \"{value}\"")
            elif key == 'stimuli':
                print(f"Change stimuli to:\n{value}")
            else:
                print(f"Change {key} to: {value}")

def update_question(question_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update a question in Supabase with the provided updates.
    
    Args:
        question_id: The ID of the question to update
        updates: Dictionary of fields to update
        
    Returns:
        Boolean indicating success
    """
    try:
        print(f"\nUpdating question {question_id}")
        result = supabase.table("questions") \
            .update(updates) \
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
        
        # Analyze question context and get suggested edits
        analysis_result = analyze_question_context(question)
        
        if analysis_result:
            message, suggested_edits = analysis_result
            display_suggested_edits(message, suggested_edits)
            
            # Create a dictionary to store approved edits
            approved_edits = {}
            
            # Get answer choices from question
            answer_choices = question.get('answer_choices', {})
            
            # Ask about each edit individually
            for key, value in suggested_edits.items():
                if key != 'reason':
                    if key.startswith('answer_choice_'):
                        print(f"\nSuggested change for answer choice {key[-1]}:")
                        print(f"Current: {answer_choices.get(key[-1], '')}")
                        print(f"Proposed: {value}")
                    elif key == 'stimuli':
                        print(f"\nSuggested change for stimuli:")
                        print(f"Current:\n{question.get('stimuli', '')}")
                        print(f"Proposed:\n{value}")
                    else:
                        print(f"\nSuggested change for {key}:")
                        print(f"Current: {question.get(key, '')}")
                        print(f"Proposed: {value}")
                    
                    while True:
                        response = input("Apply this change? (y/n/skip): ").lower()
                        if response in ['y', 'n', 'skip']:
                            if response == 'y':
                                approved_edits[key] = value
                            elif response == 'skip':
                                print("\nSkipping remaining edits...")
                                return
                            break
                        else:
                            print("Please enter 'y' for yes, 'n' for no, or 'skip' to exit")
            
            # Apply approved edits if any
            if approved_edits:
                success = update_question(question['id'], approved_edits)
                if success:
                    print("Successfully applied approved edits")
                else:
                    print("Failed to apply edits")
        
        # Add a blank line for readability
        print("\n")

if __name__ == "__main__":
    main() 