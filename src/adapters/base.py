from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import httpx
from ..models.core import (
    Job, Quote, Worker, Location, ServiceType, 
    MovementRequest, JobUpdate, JobStatus
)

class ProviderAdapter(ABC):
    """Base class for all provider adapters"""
    
    def __init__(self, provider_id: str, api_key: str, base_url: str):
        self.provider_id = provider_id
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @abstractmethod
    async def get_quote(self, request: MovementRequest) -> Optional[Quote]:
        """Get a quote for a movement request"""
        pass
    
    @abstractmethod
    async def create_job(self, quote_id: str, request: MovementRequest) -> Job:
        """Create a job from an accepted quote"""
        pass
    
    @abstractmethod
    async def get_job_status(self, job_id: str) -> JobUpdate:
        """Get current status of a job"""
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        pass
    
    @abstractmethod
    async def get_available_workers(self, location: Location, radius_km: float = 10.0) -> List[Worker]:
        """Get available workers near a location"""
        pass
    
    @abstractmethod
    async def track_job(self, job_id: str) -> Optional[Location]:
        """Get real-time location of assigned worker"""
        pass
    
    @property
    @abstractmethod
    def supported_service_types(self) -> List[ServiceType]:
        """Return list of service types this provider supports"""
        pass
    
    @property
    @abstractmethod
    def coverage_areas(self) -> List[str]:
        """Return list of geographic areas this provider covers"""
        pass
    
    async def health_check(self) -> bool:
        """Check if the provider service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        """Clean up resources"""
        await self.client.aclose()
    
    def _standardize_location(self, provider_location: Dict[str, Any]) -> Location:
        """Convert provider-specific location format to standard Location"""
        # This would be implemented differently for each provider
        return Location(
            latitude=provider_location.get("lat", 0.0),
            longitude=provider_location.get("lng", 0.0),
            address=provider_location.get("address"),
            city=provider_location.get("city"),
            state=provider_location.get("state"),
            country=provider_location.get("country"),
            postal_code=provider_location.get("postal_code")
        )
    
    def _standardize_worker(self, provider_worker: Dict[str, Any]) -> Worker:
        """Convert provider-specific worker format to standard Worker"""
        # This would be implemented differently for each provider
        return Worker(
            id=f"{self.provider_id}_{provider_worker.get('id')}",
            name=provider_worker.get("name", "Unknown"),
            phone=provider_worker.get("phone"),
            email=provider_worker.get("email"),
            rating=provider_worker.get("rating"),
            provider_id=self.provider_id,
            provider_worker_id=str(provider_worker.get("id"))
        )
