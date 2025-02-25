#!/usr/bin/env python
"""
Test script for the question content preprocessor.

This script tests the preprocessing function to ensure it correctly removes
misleading text about non-existent passages and fixes HTML tags.
"""

import os
import sys
import argparse

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the preprocessing function and grader
from app.services.grader_service import preprocess_question_content, grader

def test_preprocessor():
    """Test the question content preprocessor with examples."""
    
    print("🧪 Testing question content preprocessor...")
    
    # Example 1: Question with the misleading passage reference
    example1 = """Read the following passage and answer the question.
Read the question carefully and select the best answer.

Which word has the same vowel sound as the word "toy"?

A. boy
B. toe
C. too
D. top

The correct answer is A. "boy".

Explanation:
The word "toy" has the vowel sound /oi/. Among the options, only "boy" has the same vowel sound /oi/. 
The other options have different vowel sounds:
B. "toe" has the long O sound /oʊ/
C. "too" has the long U sound /u/
D. "top" has the short O sound /ɑ/"""

    # Example 2: Question with HTML tags
    example2 = """<p>Read the question carefully and select the best answer.</p>

<p>What is the main idea of the paragraph?</p>

<p>A. Animals communicate in different ways</p>
<p>B. Whales are the largest mammals</p>
<p>C. The ocean is a noisy place</p>
<p>D. Scientists study whale sounds</p>

<p>The correct answer is A.</p>"""

    # Example 3: Question with both issues
    example3 = """<div>Read the following passage and answer the question.
Read the question carefully and select the best answer.</div>

<p>What is 24 ÷ 8?</p>

<p>A. 3</p>
<p>B. 4</p>
<p>C. 6</p>
<p>D. 8</p>

<p>The correct answer is A.</p>"""

    # Process each example
    processed1 = preprocess_question_content(example1)
    processed2 = preprocess_question_content(example2)
    processed3 = preprocess_question_content(example3)
    
    # Print results
    print("\n📝 Example 1 (Passage Reference):")
    print("  Before preprocessing:")
    print(f"    First 50 chars: '{example1[:50]}...'")
    print("  After preprocessing:")
    print(f"    First 50 chars: '{processed1[:50]}...'")
    print(f"  Was modified: {processed1 != example1}")
    
    print("\n📝 Example 2 (HTML Tags):")
    print("  Before preprocessing:")
    print(f"    First 50 chars: '{example2[:50]}...'")
    print("  After preprocessing:")
    print(f"    First 50 chars: '{processed2[:50]}...'")
    print(f"  Was modified: {processed2 != example2}")
    
    print("\n📝 Example 3 (Both Issues):")
    print("  Before preprocessing:")
    print(f"    First 50 chars: '{example3[:50]}...'")
    print("  After preprocessing:")
    print(f"    First 50 chars: '{processed3[:50]}...'")
    print(f"  Was modified: {processed3 != example3}")
    
    # Test with the grader
    print("\n🧠 Testing grading with preprocessor...")
    metadata = {"grade_level": 4}
    
    # Grade example with problematic text
    result = grader.grade_content(example1, metadata)
    print(f"\nExample 1 grading result: {result['overall_result']}")
    print(f"Was preprocessed: {result.get('preprocessed', False)}")
    if 'critical_issues' in result and result['critical_issues']:
        print(f"Critical issues: {', '.join(result['critical_issues'])}")
    
    return 0

if __name__ == "__main__":
    sys.exit(test_preprocessor()) 