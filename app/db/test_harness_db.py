from typing import List, Optional
from datetime import datetime
import json
from supabase import create_client, Client
from app.models.test_harness import TestExample, QualityMetrics

class TestHarnessDB:
    """Database service for managing test examples"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
        
    async def init_tables(self):
        """Initialize required tables if they don't exist"""
        # Note: This is a simplified version. In practice, you'd use proper migrations
        await self.client.table("test_examples").execute()
        await self.client.table("quality_metrics").execute()
        
    async def add_example(self, example: TestExample) -> str:
        """Add a new test example to the database"""
        data = example.dict(exclude={'id'})
        data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = datetime.utcnow().isoformat()
        
        result = await self.client.table("test_examples").insert(data).execute()
        return result.data[0]['id']
        
    async def get_example(self, example_id: str) -> Optional[TestExample]:
        """Retrieve a test example by ID"""
        result = await self.client.table("test_examples").select("*").eq('id', example_id).execute()
        if result.data:
            return TestExample(**result.data[0])
        return None
        
    async def get_examples_by_lesson(self, lesson: str) -> List[TestExample]:
        """Get all test examples for a specific lesson"""
        result = await self.client.table("test_examples").select("*").eq('lesson', lesson).execute()
        return [TestExample(**row) for row in result.data]
        
    async def get_examples_by_criterion(self, criterion: str) -> List[TestExample]:
        """Get all test examples for a specific quality criterion"""
        result = await self.client.table("test_examples").select("*").eq('quality_criterion', criterion).execute()
        return [TestExample(**row) for row in result.data]
        
    async def update_example(self, example: TestExample):
        """Update an existing test example"""
        data = example.dict(exclude={'id'})
        data['updated_at'] = datetime.utcnow().isoformat()
        
        await self.client.table("test_examples").update(data).eq('id', example.id).execute()
        
    async def delete_example(self, example_id: str):
        """Delete a test example"""
        await self.client.table("test_examples").delete().eq('id', example_id).execute()
        
    async def save_metrics(self, metrics: QualityMetrics):
        """Save current quality metrics"""
        data = metrics.dict()
        data['last_updated'] = datetime.utcnow().isoformat()
        
        # Store as a new record - we want to keep history
        await self.client.table("quality_metrics").insert(data).execute()
        
    async def get_latest_metrics(self) -> Optional[QualityMetrics]:
        """Get the most recent quality metrics"""
        result = await self.client.table("quality_metrics").select("*").order('last_updated', desc=True).limit(1).execute()
        if result.data:
            return QualityMetrics(**result.data[0])
        return None
        
    async def get_examples_by_mutation(self, mutation_type: str) -> List[TestExample]:
        """Get all test examples with a specific mutation type"""
        result = await self.client.table("test_examples").select("*").eq('mutation_type', mutation_type).execute()
        return [TestExample(**row) for row in result.data]
        
    async def get_failed_examples(self) -> List[TestExample]:
        """Get all examples that failed quality checks"""
        result = await self.client.table("test_examples").select("*").eq('quality_status', 'bad').execute()
        return [TestExample(**row) for row in result.data] 