from typing import List, Dict, Optional
import openai
from datetime import datetime
from app.models.test_harness import (
    TestExample,
    QualityCheckResult,
    QualityMetrics,
    QualityCriterion,
    QualityStatus,
    MutationType
)

class QualityControlService:
    """Service for managing quality control of educational content"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
        self.metrics = QualityMetrics()
        
    async def check_quality(self, content: str, lesson: str, difficulty_level: str) -> QualityCheckResult:
        """
        Check the quality of a question against all criteria
        Returns a QualityCheckResult with detailed feedback
        """
        result = QualityCheckResult()
        criterion_prompts = {
            QualityCriterion.VOCABULARY: """
                Evaluate if the vocabulary in this Grade 4 Language Arts question is grade-appropriate.
                Consider:
                1. Word complexity matches Grade 4 level
                2. Technical terms are properly introduced
                3. No unnecessarily complex words
                Question: {content}
            """,
            QualityCriterion.QUESTION_STEM: """
                Evaluate if the question stem is clear and well-structured for Grade 4.
                Consider:
                1. Clear and direct wording
                2. Single, focused task
                3. No ambiguity
                Question: {content}
            """,
            QualityCriterion.DISTRACTORS: """
                Evaluate if the multiple-choice distractors are plausible and well-designed.
                Consider:
                1. All distractors are plausible
                2. No obviously wrong answers
                3. Distractors test common misconceptions
                Question: {content}
            """,
            # Add other criteria prompts...
        }
        
        all_scores = {}
        failed_criteria = []
        
        for criterion, prompt in criterion_prompts.items():
            formatted_prompt = prompt.format(content=content)
            response = await self._evaluate_with_gpt(formatted_prompt)
            score = self._parse_quality_score(response)
            all_scores[criterion] = score
            
            if score < 0.9:  # We require very high quality
                failed_criteria.append(criterion)
        
        result.criterion_scores = all_scores
        result.failed_criteria = failed_criteria
        result.passed = len(failed_criteria) == 0
        result.feedback = await self._generate_feedback(failed_criteria, content)
        
        return result
    
    async def generate_mutations(self, example: TestExample) -> List[TestExample]:
        """
        Generate bad examples by mutating a good example
        Returns a list of mutated examples
        """
        mutations = []
        
        mutation_prompts = {
            MutationType.VOCABULARY_MUTATION: """
                Modify this question to use inappropriate vocabulary for Grade 4:
                {content}
            """,
            MutationType.STEM_MUTATION: """
                Make this question stem unclear or ambiguous:
                {content}
            """,
            # Add other mutation prompts...
        }
        
        for mutation_type, prompt in mutation_prompts.items():
            formatted_prompt = prompt.format(content=example.content)
            mutated_content = await self._generate_with_gpt(formatted_prompt)
            
            mutations.append(
                TestExample(
                    content=mutated_content,
                    quality_status=QualityStatus.BAD,
                    quality_criterion=example.quality_criterion,
                    mutation_type=mutation_type,
                    lesson=example.lesson,
                    difficulty_level=example.difficulty_level,
                    metadata={"original_id": example.id}
                )
            )
        
        return mutations
    
    def update_metrics(self, check_result: QualityCheckResult):
        """Update quality metrics based on a new check result"""
        self.metrics.total_examples += 1
        if check_result.passed:
            self.metrics.good_examples += 1
        else:
            self.metrics.bad_examples += 1
            
        # Update precision, recall, and F1 score
        if self.metrics.total_examples > 0:
            self.metrics.precision = self.metrics.good_examples / self.metrics.total_examples
            # Note: Recall would require ground truth data
            if self.metrics.precision > 0:  # Avoid division by zero
                self.metrics.f1_score = 2 * (self.metrics.precision * self.metrics.recall) / (self.metrics.precision + self.metrics.recall)
        
        # Update criterion-specific metrics
        for criterion, score in check_result.criterion_scores.items():
            if criterion not in self.metrics.metrics_by_criterion:
                self.metrics.metrics_by_criterion[criterion] = {"total": 0, "passed": 0}
            self.metrics.metrics_by_criterion[criterion]["total"] += 1
            if score >= 0.9:
                self.metrics.metrics_by_criterion[criterion]["passed"] += 1
                
        self.metrics.last_updated = datetime.utcnow()
    
    async def _evaluate_with_gpt(self, prompt: str) -> str:
        """Evaluate content quality using GPT-4"""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a strict educational content evaluator for Grade 4 Language Arts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error evaluating with GPT: {str(e)}")
    
    async def _generate_with_gpt(self, prompt: str) -> str:
        """Generate content using GPT-4"""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are an educational content generator for Grade 4 Language Arts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error generating with GPT: {str(e)}")
    
    def _parse_quality_score(self, gpt_response: str) -> float:
        """Parse GPT's response into a quality score between 0 and 1"""
        # Implement parsing logic based on GPT's response format
        # This is a simplified version - you'd want more robust parsing
        if "excellent" in gpt_response.lower():
            return 1.0
        elif "good" in gpt_response.lower():
            return 0.8
        elif "acceptable" in gpt_response.lower():
            return 0.6
        else:
            return 0.4
    
    async def _generate_feedback(self, failed_criteria: List[QualityCriterion], content: str) -> str:
        """Generate detailed feedback for failed criteria"""
        if not failed_criteria:
            return "All quality criteria passed."
            
        prompt = f"""
            Generate specific feedback for improving this Grade 4 Language Arts question:
            Question: {content}
            Failed criteria: {', '.join([c.value for c in failed_criteria])}
            Provide specific suggestions for each criterion.
        """
        
        feedback = await self._generate_with_gpt(prompt)
        return feedback 