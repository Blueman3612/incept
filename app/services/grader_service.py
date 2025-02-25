"""
Quality Control Grader Service

This service evaluates educational content quality based on four key metrics:
1. Completeness - Are all required components present?
2. Answer Quality - Are the answers and distractors well-formed?
3. Explanation Quality - Are the explanations clear and educational?
4. Language Quality - Is the language grade-appropriate and grammatically correct?

The service uses OpenAI's GPT-4 to evaluate content against these metrics and provides
detailed feedback for improvements when quality standards aren't met.
"""

import os
import json
import logging
import requests
import re
from typing import Dict, Any, Tuple, List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def preprocess_question_content(content: str) -> str:
    """
    Preprocess question content to remove misleading boilerplate text that could trigger false critical issues.
    
    Args:
        content: The raw question content
        
    Returns:
        Cleaned question content
    """
    # Pattern to match the misleading passage reference with the following instruction
    pattern = r"Read the following passage and answer the question\.\s*Read the question carefully and select the best answer\."
    
    # Replace with just the second instruction
    cleaned_content = re.sub(pattern, "Read the question carefully and select the best answer.", content)
    
    # Handle case where "Read the following passage and answer the question." is followed by a passage
    # that might be duplicated later in HTML format
    passage_intro_pattern = r"Read the following passage and answer the question\.\s*\n\s*(.+?)(?=\n\s*<|\n\s*What|\n\s*[A-Z]\))"
    
    # Look for matches of the passage introduction pattern
    match = re.search(passage_intro_pattern, cleaned_content, re.DOTALL)
    
    if match:
        # Get the plain text passage
        passage_text = match.group(1).strip()
        
        # Only proceed if we have a substantial passage (not just a single short line)
        if passage_text and len(passage_text) > 15:
            # Create simplified versions for comparison (removing formatting, case, punctuation)
            simplified_passage = re.sub(r'[^\w\s]', '', passage_text).lower().strip()
            simplified_content = re.sub(r'[^\w\s]', '', cleaned_content).lower()
            
            # Check for a second occurrence of this passage
            start_pos = simplified_content.find(simplified_passage)
            if start_pos >= 0:
                second_pos = simplified_content.find(simplified_passage, start_pos + len(simplified_passage))
                if second_pos >= 0:
                    # Found a duplicate! Remove the first occurrence and the intro
                    cleaned_content = cleaned_content[:match.start()] + cleaned_content[match.end():]
                    logger.info(f"Removed duplicated passage: {passage_text[:50]}...")
    
    # Also look for any HTML tables containing the passage
    html_table_pattern = r"<table[^>]*>.*?</table>\s*<br>"
    match = re.search(html_table_pattern, cleaned_content, re.DOTALL)
    if match:
        # Extract text from the table
        table_html = match.group(0)
        # Create a version without the table but with the text content preserved
        text_only_version = re.sub(r'<[^>]*>', ' ', table_html).strip()
        # Replace the HTML table with just the text
        if text_only_version:
            cleaned_content = cleaned_content.replace(table_html, text_only_version + "\n\n")
            logger.info("Converted HTML table to plain text")
    
    # Finally, remove any remaining HTML tags
    cleaned_content = re.sub(r"<[^>]*>", "", cleaned_content)
    
    # If content was modified, log that preprocessing was applied
    if cleaned_content != content:
        logger.info("Preprocessing applied to question content")
    
    return cleaned_content


class QualityGrader:
    """
    Evaluates the quality of educational content based on predefined criteria.
    Uses OpenAI's GPT-4 to analyze content and provide quality scores and feedback.
    """
    
    def __init__(self):
        """Initialize the QualityGrader with API settings."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is missing. Please set the OPENAI_API_KEY environment variable.")
        
        self.model = os.getenv("GPT_MODEL", "gpt-4")
        
        # Even stricter thresholds for quality assurance
        self.passing_threshold = 0.85
        self.minimum_criterion_threshold = 0.75
        self.critical_criteria = ["answer_quality", "completeness", "educational_value"]  # Added educational_value
        self.critical_threshold = 0.85
        
        # Define the scoring rubric for each quality criterion
        self.rubric = {
            "completeness": {
                "description": "All required components are present and fully developed.",
                "components": [
                    "Question stem with clear prompt",
                    "Answer options (for MCQ)",
                    "Correct answer identification",
                    "Explanations for wrong answers (for MCQ)",
                    "Step-by-step solution"
                ],
                "critical_issues": [
                    "Missing question stem",
                    "Missing answer options for MCQ",
                    "No clear correct answer",
                    "Missing explanations for wrong answers",
                    "No solution provided",
                    "Components present but severely underdeveloped"  # New critical issue
                ]
            },
            "answer_quality": {
                "description": "Answers and distractors are well-designed and educationally sound.",
                "components": [
                    "Single unambiguously correct answer",
                    "Plausible distractors (for MCQ)",
                    "No obviously incorrect distractors",
                    "Distractors that test common misconceptions",
                    "Correct answer doesn't stand out based on length/format"
                ],
                "critical_issues": [
                    "Multiple potentially correct answers",
                    "Implausible distractors that don't test understanding",
                    "Distractors that are obviously wrong",
                    "Correct answer is identifiable by format or pattern",
                    "Distractors don't test meaningful misconceptions",  # New critical issue
                    "Answer options too similar or too different"  # New critical issue
                ]
            },
            "explanation_quality": {
                "description": "Explanations are clear, accurate, and educational.",
                "components": [
                    "Correct solution explained step-by-step",
                    "Clear reasoning for each step",
                    "Specific explanations for why distractors are wrong",
                    "Educational value in explanations",
                    "Appropriate level of detail"
                ],
                "critical_issues": [
                    "Incorrect explanation",
                    "Confusing or misleading explanations",
                    "Explanations that don't address misconceptions",
                    "Overly complex explanations for grade level",
                    "Superficial explanations that just restate the answer",  # New critical issue
                    "Generic explanations that don't tie to specific content"  # New critical issue
                ]
            },
            "language_quality": {
                "description": "Language is grade-appropriate, clear, and grammatically correct.",
                "components": [
                    "Grade-appropriate vocabulary",
                    "Clear and unambiguous wording",
                    "Correct grammar and punctuation",
                    "Consistent terminology",
                    "Well-formatted text"
                ],
                "critical_issues": [
                    "Vocabulary significantly above/below grade level",
                    "Ambiguous or confusing wording",
                    "Severe grammar or punctuation errors",
                    "Inconsistent terminology that affects understanding",
                    "Wordiness that obscures meaning",  # New critical issue
                    "Overly complex sentence structures for grade level"  # New critical issue
                ]
            },
            "educational_value": {  # New criterion
                "description": "Content has clear educational value and supports learning objectives.",
                "components": [
                    "Tests important grade-level knowledge",
                    "Focuses on meaningful concepts",
                    "Promotes critical thinking",
                    "Relates to real-world application when appropriate",
                    "Aligned with educational standards"
                ],
                "critical_issues": [
                    "Trivial or non-educational content",
                    "Tests rote memorization only",
                    "Lacks connection to important concepts",
                    "Content inappropriate for grade level",
                    "Could be answered without understanding the concept"
                ]
            }
        }
    
    def grade_content(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Grade the provided content against quality criteria.
        
        Args:
            content: The educational content to evaluate
            metadata: Optional metadata about the content (e.g., expected grade level)
            
        Returns:
            Dict containing scores, feedback, overall pass/fail determination,
            and any critical issues identified
        """
        logger.info("Grading content quality...")
        
        # Ensure we have content to grade
        if not content or not content.strip():
            return {
                "overall_result": "fail",
                "message": "No content provided for grading.",
                "scores": {
                    "completeness": 0.0,
                    "answer_quality": 0.0,
                    "explanation_quality": 0.0,
                    "language_quality": 0.0,
                    "educational_value": 0.0  # Added new criterion
                },
                "critical_issues": ["No content provided"],
                "feedback": {
                    "completeness": "No content provided.",
                    "answer_quality": "No content provided.",
                    "explanation_quality": "No content provided.",
                    "language_quality": "No content provided.",
                    "educational_value": "No content provided."  # Added new criterion
                }
            }
        
        # Preprocess the content to remove misleading text and HTML tags
        preprocessed_content = preprocess_question_content(content)
        
        # Get grade level from metadata if available
        grade_level = metadata.get("grade_level", 4) if metadata else 4
        
        # Get scores, feedback, and critical issues from LLM evaluation
        scores, feedback, critical_issues, confidence = self._evaluate_with_llm(preprocessed_content, grade_level)
        
        # Apply the stricter evaluation logic
        criteria_results = {}
        failing_criteria = []
        
        # Check each criterion against thresholds
        for criterion, score in scores.items():
            # Critical criteria have higher thresholds
            threshold = self.critical_threshold if criterion in self.critical_criteria else self.minimum_criterion_threshold
            passes = score >= threshold
            
            criteria_results[criterion] = passes
            
            if not passes:
                failing_criteria.append(criterion)
        
        # Overall pass requires all criteria to pass, no critical issues, and high confidence
        overall_pass = (
            len(failing_criteria) == 0 and 
            len(critical_issues) == 0 and 
            confidence >= 0.90 and  # Increased from 0.85
            all(scores.get(key, 0) >= self.critical_threshold for key in self.critical_criteria)
        )
        
        # Additional check: verify adequate spread between scores
        # If all scores are exactly the same, it's suspicious
        score_values = list(scores.values())
        if len(set(score_values)) <= 1 and score_values[0] > 0.8:
            critical_issues.append("Suspicious uniform scoring pattern")
            overall_pass = False
            
        # Determine failure reason with more detail
        failure_reason = None
        if not overall_pass:
            if confidence < 0.90:
                failure_reason = f"Low evaluation confidence: {confidence:.2f}"
            elif len(critical_issues) > 0:
                failure_reason = f"Critical issues identified: {', '.join(critical_issues[:3])}"
            elif len(failing_criteria) > 0:
                failure_detail = []
                for criterion in failing_criteria:
                    failure_detail.append(f"{criterion} ({scores.get(criterion, 0):.2f})")
                failure_reason = f"Failed criteria: {', '.join(failure_detail)}"
            else:
                # Catch-all for any other failures
                failure_reason = "Failed to meet overall quality standard"
        
        # Prepare the detailed response
        result = {
            "overall_result": "pass" if overall_pass else "fail",
            "message": "Content meets all quality standards." if overall_pass else 
                      f"Content does not meet quality standards. {failure_reason}",
            "scores": scores,
            "criteria_results": criteria_results,
            "critical_issues": critical_issues,
            "confidence": confidence,
            "feedback": feedback,
            "failure_reason": failure_reason if not overall_pass else None,
            "preprocessed": preprocessed_content != content  # Flag if preprocessing was applied
        }
        
        # Log the reason for failure if applicable
        if not overall_pass:
            details = []
            if confidence < 0.90:  # Updated threshold
                details.append(f"Confidence score ({confidence:.2f}) is below threshold (0.90)")
            if critical_issues:
                details.append(f"Critical issues detected: {', '.join(critical_issues)}")
            for criterion, passes in criteria_results.items():
                if not passes:
                    threshold = self.critical_threshold if criterion in self.critical_criteria else self.minimum_criterion_threshold
                    details.append(f"{criterion} score ({scores[criterion]:.2f}) is below required threshold ({threshold:.2f})")
            
            logger.info(f"Content failed quality check: {'; '.join(details)}")
        
        return result
    
    def _evaluate_with_llm(self, content: str, grade_level: int) -> Tuple[Dict[str, float], Dict[str, str], List[str], float]:
        """
        Use OpenAI API to evaluate content quality.
        
        Args:
            content: The content to evaluate
            grade_level: The target grade level for the content
            
        Returns:
            Tuple of (scores_dict, feedback_dict, critical_issues_list, confidence_score)
        """
        try:
            # Construct the evaluation prompt
            prompt = self._build_evaluation_prompt(content, grade_level)
            
            # Make the API request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert educational content evaluator with expertise in K-8 education standards and content quality assessment. You are extremely critical and hold content to the highest standards. You never give high scores unless content is truly exceptional."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,  # Lower temperature for more consistent evaluations
                "max_tokens": 2000
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return self._default_error_response()
            
            result = response.json()
            response_text = result["choices"][0]["message"]["content"].strip()
            
            # Parse the evaluation response
            return self._parse_evaluation_response(response_text)
            
        except Exception as e:
            logger.exception(f"Error evaluating content: {str(e)}")
            return self._default_error_response()
    
    def _build_evaluation_prompt(self, content: str, grade_level: int) -> str:
        """
        Build a comprehensive prompt for evaluating content quality.
        
        Args:
            content: The content to evaluate
            grade_level: The target grade level
            
        Returns:
            String prompt for the LLM
        """
        # Construct a detailed prompt that covers all five quality criteria (including the new educational_value)
        prompt = f"""
You are an expert reviewer of educational content for Grade {grade_level} with extremely high standards.
You'll evaluate a piece of educational content against five specific quality criteria, providing a score and detailed feedback.

Important: Educational content MUST be of the highest quality. Be EXTREMELY strict and critical in your evaluation.
Err on the side of failing content when in doubt. It's far better to reject good content than to allow bad content through.
Do not give high scores (0.9+) unless the content is truly excellent in that dimension.

CONTENT TO EVALUATE:
```
{content}
```

EVALUATION CRITERIA:

1. COMPLETENESS (Score 0.0-1.0)
   Definition: {self.rubric['completeness']['description']}
   Components to look for:
   - {self.rubric['completeness']['components'][0]}
   - {self.rubric['completeness']['components'][1]}
   - {self.rubric['completeness']['components'][2]}
   - {self.rubric['completeness']['components'][3]}
   - {self.rubric['completeness']['components'][4]}
   Critical issues to check for:
   - {self.rubric['completeness']['critical_issues'][0]}
   - {self.rubric['completeness']['critical_issues'][1]}
   - {self.rubric['completeness']['critical_issues'][2]}
   - {self.rubric['completeness']['critical_issues'][3]}
   - {self.rubric['completeness']['critical_issues'][5]}

2. ANSWER QUALITY (Score 0.0-1.0)
   Definition: {self.rubric['answer_quality']['description']}
   Components to look for:
   - {self.rubric['answer_quality']['components'][0]}
   - {self.rubric['answer_quality']['components'][1]}
   - {self.rubric['answer_quality']['components'][2]}
   - {self.rubric['answer_quality']['components'][3]}
   - {self.rubric['answer_quality']['components'][4]}
   Critical issues to check for:
   - {self.rubric['answer_quality']['critical_issues'][0]}
   - {self.rubric['answer_quality']['critical_issues'][1]}
   - {self.rubric['answer_quality']['critical_issues'][2]}
   - {self.rubric['answer_quality']['critical_issues'][3]}
   - {self.rubric['answer_quality']['critical_issues'][4]}
   - {self.rubric['answer_quality']['critical_issues'][5]}

3. EXPLANATION QUALITY (Score 0.0-1.0)
   Definition: {self.rubric['explanation_quality']['description']}
   Components to look for:
   - {self.rubric['explanation_quality']['components'][0]}
   - {self.rubric['explanation_quality']['components'][1]}
   - {self.rubric['explanation_quality']['components'][2]}
   - {self.rubric['explanation_quality']['components'][3]}
   - {self.rubric['explanation_quality']['components'][4]}
   Critical issues to check for:
   - {self.rubric['explanation_quality']['critical_issues'][0]}
   - {self.rubric['explanation_quality']['critical_issues'][1]}
   - {self.rubric['explanation_quality']['critical_issues'][2]}
   - {self.rubric['explanation_quality']['critical_issues'][3]}
   - {self.rubric['explanation_quality']['critical_issues'][4]}
   - {self.rubric['explanation_quality']['critical_issues'][5]}

4. LANGUAGE QUALITY (Score 0.0-1.0)
   Definition: {self.rubric['language_quality']['description']}
   Components to look for:
   - {self.rubric['language_quality']['components'][0]}
   - {self.rubric['language_quality']['components'][1]}
   - {self.rubric['language_quality']['components'][2]}
   - {self.rubric['language_quality']['components'][3]}
   - {self.rubric['language_quality']['components'][4]}
   Critical issues to check for:
   - {self.rubric['language_quality']['critical_issues'][0]}
   - {self.rubric['language_quality']['critical_issues'][1]}
   - {self.rubric['language_quality']['critical_issues'][2]}
   - {self.rubric['language_quality']['critical_issues'][3]}
   - {self.rubric['language_quality']['critical_issues'][4]}
   - {self.rubric['language_quality']['critical_issues'][5]}

5. EDUCATIONAL VALUE (Score 0.0-1.0)
   Definition: {self.rubric['educational_value']['description']}
   Components to look for:
   - {self.rubric['educational_value']['components'][0]}
   - {self.rubric['educational_value']['components'][1]}
   - {self.rubric['educational_value']['components'][2]}
   - {self.rubric['educational_value']['components'][3]}
   - {self.rubric['educational_value']['components'][4]}
   Critical issues to check for:
   - {self.rubric['educational_value']['critical_issues'][0]}
   - {self.rubric['educational_value']['critical_issues'][1]}
   - {self.rubric['educational_value']['critical_issues'][2]}
   - {self.rubric['educational_value']['critical_issues'][3]}
   - {self.rubric['educational_value']['critical_issues'][4]}

SCORING GUIDELINES:
Use a fine-grained scale from 0.0 to 1.0 with increments of 0.05 to allow for nuanced evaluation:
- 0.00-0.40: Severely deficient, unacceptable
- 0.45-0.60: Significant issues present
- 0.65-0.75: Some issues, needs improvement
- 0.80-0.85: Minor issues, generally acceptable
- 0.90-0.95: Very good, meets requirements well
- 1.00: Exceptional, perfect (extremely rare)

IMPORTANT: Be very stingy with high scores. Reserve scores of 0.9+ only for truly exceptional content.
Most content, even good content, should score between 0.75-0.85 in each category.
Be especially critical with educational value - does this content truly teach something meaningful?

For each criterion, provide:
1. A score between 0.0 and 1.0 using the increments described above
2. Detailed feedback explaining the score, including specific examples from the content
3. List of any critical issues identified (issues that would automatically cause a fail)

Also provide a confidence score (0.0-1.0) indicating how confident you are in your evaluation.

FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:
```json
{{
  "scores": {{
    "completeness": [SCORE],
    "answer_quality": [SCORE],
    "explanation_quality": [SCORE],
    "language_quality": [SCORE],
    "educational_value": [SCORE]
  }},
  "feedback": {{
    "completeness": "[DETAILED FEEDBACK]",
    "answer_quality": "[DETAILED FEEDBACK]",
    "explanation_quality": "[DETAILED FEEDBACK]",
    "language_quality": "[DETAILED FEEDBACK]",
    "educational_value": "[DETAILED FEEDBACK]"
  }},
  "critical_issues": [
    "[CRITICAL ISSUE 1]",
    "[CRITICAL ISSUE 2]"
  ],
  "confidence": [CONFIDENCE SCORE]
}}
```

Be extremely critical and hold the content to the highest standards for Grade {grade_level}.
Again, it is better to fail good content than to pass bad content.
"""
        return prompt
    
    def _parse_evaluation_response(self, response_text: str) -> Tuple[Dict[str, float], Dict[str, str], List[str], float]:
        """
        Parse the LLM's evaluation response into structured data.
        
        Args:
            response_text: The raw text response from the LLM
            
        Returns:
            Tuple of (scores_dict, feedback_dict, critical_issues_list, confidence_score)
        """
        try:
            # Extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)
                
                scores = data.get("scores", {})
                feedback = data.get("feedback", {})
                critical_issues = data.get("critical_issues", [])
                confidence = data.get("confidence", 0.5)  # Default to moderate confidence
                
                # If critical issues is not a list, convert it to one
                if isinstance(critical_issues, str):
                    critical_issues = [critical_issues]
                
                # Ensure all required keys are present
                for key in ["completeness", "answer_quality", "explanation_quality", "language_quality", "educational_value"]:
                    if key not in scores:
                        scores[key] = 0.0
                    if key not in feedback:
                        feedback[key] = f"No feedback provided for {key}."
                
                return scores, feedback, critical_issues, confidence
            else:
                logger.error(f"Failed to parse JSON from response: {response_text}")
                return self._default_error_response()
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from response: {response_text}")
            return self._default_error_response()
        except Exception as e:
            logger.exception(f"Error parsing evaluation response: {str(e)}")
            return self._default_error_response()
    
    def _default_error_response(self) -> Tuple[Dict[str, float], Dict[str, str], List[str], float]:
        """
        Provide default error response values when evaluation fails.
        
        Returns:
            Tuple of (default_scores, default_feedback, default_critical_issues, default_confidence)
        """
        default_scores = {
            "completeness": 0.0,
            "answer_quality": 0.0,
            "explanation_quality": 0.0,
            "language_quality": 0.0,
            "educational_value": 0.0  # Added new criterion
        }
        
        default_feedback = {
            "completeness": "Error evaluating content completeness.",
            "answer_quality": "Error evaluating answer quality.",
            "explanation_quality": "Error evaluating explanation quality.",
            "language_quality": "Error evaluating language quality.",
            "educational_value": "Error evaluating educational value."  # Added new criterion
        }
        
        default_critical_issues = ["Evaluation system error"]
        default_confidence = 0.0
        
        return default_scores, default_feedback, default_critical_issues, default_confidence


# Create a singleton instance for use across the application
grader = QualityGrader()

def grade_question(content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Grade a question against our quality standards.
    
    Args:
        content: The question content to evaluate
        metadata: Optional metadata about the question
        
    Returns:
        Grading results including scores, feedback, and pass/fail status
    """
    return grader.grade_content(content, metadata) 