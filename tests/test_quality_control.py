import pytest
from datetime import datetime
import os
from app.models.test_harness import (
    TestExample,
    QualityStatus,
    QualityCriterion,
    MutationType,
    DifficultyLevel
)
from app.services.quality_control import QualityControlService
from app.db.test_harness_db import TestHarnessDB

# Example test data
SAMPLE_GOOD_QUESTION = """
What is the main idea of the following paragraph?

The rainforest is home to many different types of animals. Colorful birds fly through the tall trees. Monkeys swing from branch to branch. Jaguars hunt on the forest floor. All these animals depend on the rainforest for food and shelter.

A) The rainforest has tall trees
B) Many animals live in the rainforest
C) Jaguars are good hunters
D) Birds are colorful
"""

@pytest.fixture
def qc_service():
    api_key = os.getenv("OPENAI_API_KEY")
    return QualityControlService(api_key)

@pytest.fixture
def db_service():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return TestHarnessDB(url, key)

@pytest.mark.asyncio
async def test_quality_check_good_example(qc_service):
    """Test quality checking with a good example"""
    result = await qc_service.check_quality(
        content=SAMPLE_GOOD_QUESTION,
        lesson="Main Idea and Supporting Details",
        difficulty_level=DifficultyLevel.MEDIUM.value
    )
    
    assert result.passed
    assert len(result.failed_criteria) == 0
    assert all(score >= 0.9 for score in result.criterion_scores.values())

@pytest.mark.asyncio
async def test_mutation_generation(qc_service):
    """Test generating mutations from a good example"""
    good_example = TestExample(
        content=SAMPLE_GOOD_QUESTION,
        quality_status=QualityStatus.GOOD,
        quality_criterion=QualityCriterion.QUESTION_STEM,
        mutation_type=MutationType.ORIGINAL,
        lesson="Main Idea and Supporting Details",
        difficulty_level=DifficultyLevel.MEDIUM,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    mutations = await qc_service.generate_mutations(good_example)
    
    assert len(mutations) > 0
    for mutation in mutations:
        assert mutation.quality_status == QualityStatus.BAD
        assert mutation.lesson == good_example.lesson
        assert mutation.difficulty_level == good_example.difficulty_level
        assert mutation.mutation_type != MutationType.ORIGINAL

@pytest.mark.asyncio
async def test_metrics_tracking(qc_service):
    """Test quality metrics tracking"""
    # First check
    result1 = await qc_service.check_quality(
        content=SAMPLE_GOOD_QUESTION,
        lesson="Main Idea and Supporting Details",
        difficulty_level=DifficultyLevel.MEDIUM.value
    )
    qc_service.update_metrics(result1)
    
    # Check metrics
    assert qc_service.metrics.total_examples == 1
    if result1.passed:
        assert qc_service.metrics.good_examples == 1
        assert qc_service.metrics.precision == 1.0
    else:
        assert qc_service.metrics.bad_examples == 1
        assert qc_service.metrics.precision == 0.0

@pytest.mark.asyncio
async def test_database_operations(db_service):
    """Test database operations"""
    # Create example
    example = TestExample(
        content=SAMPLE_GOOD_QUESTION,
        quality_status=QualityStatus.GOOD,
        quality_criterion=QualityCriterion.QUESTION_STEM,
        mutation_type=MutationType.ORIGINAL,
        lesson="Main Idea and Supporting Details",
        difficulty_level=DifficultyLevel.MEDIUM,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Add to database
    example_id = await db_service.add_example(example)
    assert example_id is not None
    
    # Retrieve and verify
    retrieved = await db_service.get_example(example_id)
    assert retrieved is not None
    assert retrieved.content == SAMPLE_GOOD_QUESTION
    assert retrieved.quality_status == QualityStatus.GOOD
    
    # Clean up
    await db_service.delete_example(example_id)
    deleted = await db_service.get_example(example_id)
    assert deleted is None

@pytest.mark.asyncio
async def test_end_to_end_workflow(qc_service, db_service):
    """Test complete workflow from creation to storage"""
    # 1. Check quality of a question
    result = await qc_service.check_quality(
        content=SAMPLE_GOOD_QUESTION,
        lesson="Main Idea and Supporting Details",
        difficulty_level=DifficultyLevel.MEDIUM.value
    )
    
    # 2. Create test example based on result
    example = TestExample(
        content=SAMPLE_GOOD_QUESTION,
        quality_status=QualityStatus.GOOD if result.passed else QualityStatus.BAD,
        quality_criterion=QualityCriterion.QUESTION_STEM,
        mutation_type=MutationType.ORIGINAL,
        lesson="Main Idea and Supporting Details",
        difficulty_level=DifficultyLevel.MEDIUM,
        metadata={"quality_check_result": result.dict()}
    )
    
    # 3. Store in database
    example_id = await db_service.add_example(example)
    
    # 4. If it's good, generate mutations
    if result.passed:
        mutations = await qc_service.generate_mutations(example)
        for mutation in mutations:
            await db_service.add_example(mutation)
            
        # Verify mutations were stored
        stored_mutations = await db_service.get_examples_by_mutation(mutations[0].mutation_type)
        assert len(stored_mutations) > 0
    
    # 5. Update and store metrics
    qc_service.update_metrics(result)
    await db_service.save_metrics(qc_service.metrics)
    
    # 6. Clean up
    await db_service.delete_example(example_id)
    
    # Verify metrics were stored
    metrics = await db_service.get_latest_metrics()
    assert metrics is not None
    assert metrics.total_examples > 0 