import asyncio
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from ..models.core import (
    Job, Quote, MovementRequest, MovementResponse, 
    JobUpdate, ServiceType, JobStatus, Location
)
from ..adapters.base import ProviderAdapter
from .router import RouteOptimizer

logger = logging.getLogger(__name__)

class TesseractsGateway:
    """Main gateway orchestrating all movement and logistics operations"""
    
    def __init__(self, providers: List[ProviderAdapter]):
        self.providers = {provider.provider_id: provider for provider in providers}
        self.router = RouteOptimizer(providers)
        self.active_jobs: Dict[str, Job] = {}
        self.active_quotes: Dict[str, Quote] = {}
    
    async def request_movement(self, request: MovementRequest) -> MovementResponse:
        """Main entry point for movement requests - returns quotes from optimal providers"""
        
        logger.info(f"Processing movement request: {request.service_type} from "
                   f"({request.pickup_location.latitude}, {request.pickup_location.longitude}) to "
                   f"({request.dropoff_location.latitude}, {request.dropoff_location.longitude})")
        
        # Get optimal quotes from routing engine
        quotes = await self.router.get_optimal_quotes(request, max_quotes=5)
        
        # Store quotes temporarily for later acceptance
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        for quote in quotes:
            self.active_quotes[quote.quote_id] = quote
        
        # Determine recommended quote (highest scored)
        recommended_quote_id = quotes[0].quote_id if quotes else None
        
        response = MovementResponse(
            request_id=request_id,
            quotes=quotes,
            recommended_quote_id=recommended_quote_id
        )
        
        logger.info(f"Returning {len(quotes)} quotes for request {request_id}")
        return response
    
    async def accept_quote(self, quote_id: str, request: MovementRequest) -> Job:
        """Accept a quote and create a job"""
        
        if quote_id not in self.active_quotes:
            raise ValueError(f"Quote {quote_id} not found or expired")
        
        quote = self.active_quotes[quote_id]
        
        # Check if quote has expired
        if datetime.utcnow() > quote.expires_at:
            raise ValueError(f"Quote {quote_id} has expired")
        
        # Get the provider adapter
        provider = self.providers.get(quote.provider_id)
        if not provider:
            raise ValueError(f"Provider {quote.provider_id} not available")
        
        # Create job with the provider
        job = await provider.create_job(quote_id, request)
        
        # Store job for tracking
        self.active_jobs[job.id] = job
        
        # Clean up the quote
        del self.active_quotes[quote_id]
        
        logger.info(f"Created job {job.id} with provider {quote.provider_id}")
        return job
    
    async def get_job_status(self, job_id: str) -> JobUpdate:
        """Get current status of a job"""
        
        if job_id not in self.active_jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.active_jobs[job_id]
        provider = self.providers.get(job.provider_id)
        
        if not provider:
            raise ValueError(f"Provider {job.provider_id} not available")
        
        # Get status from provider
        job_update = await provider.get_job_status(job_id)
        
        # Update our local job state
        job.status = job_update.status
        job.updated_at = datetime.utcnow()
        
        logger.debug(f"Job {job_id} status: {job_update.status}")
        return job_update
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        
        if job_id not in self.active_jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.active_jobs[job_id]
        provider = self.providers.get(job.provider_id)
        
        if not provider:
            raise ValueError(f"Provider {job.provider_id} not available")
        
        # Cancel with provider
        success = await provider.cancel_job(job_id)
        
        if success:
            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.utcnow()
            logger.info(f"Cancelled job {job_id}")
        
        return success
    
    async def track_job(self, job_id: str) -> Optional[Location]:
        """Get real-time location of a job"""
        
        if job_id not in self.active_jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.active_jobs[job_id]
        provider = self.providers.get(job.provider_id)
        
        if not provider:
            return None
        
        return await provider.track_job(job_id)
    
    async def get_available_workers(
        self, 
        location: Location, 
        service_type: ServiceType,
        radius_km: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Get available workers from all providers near a location"""
        
        worker_tasks = []
        for provider in self.providers.values():
            if service_type in provider.supported_service_types:
                worker_tasks.append(provider.get_available_workers(location, radius_km))
        
        if not worker_tasks:
            return []
        
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)
        
        # Flatten and aggregate workers from all providers
        all_workers = []
        for result in worker_results:
            if isinstance(result, list):
                all_workers.extend(result)
        
        # Convert to dict format for API response
        return [
            {
                "id": worker.id,
                "name": worker.name,
                "rating": worker.rating,
                "vehicle_type": worker.vehicle.type if worker.vehicle else None,
                "provider": worker.provider_id,
                "distance_km": self._calculate_distance(location, worker.current_location) if worker.current_location else None
            }
            for worker in all_workers
        ]
    
    def _calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """Calculate distance between locations"""
        lat_diff = abs(loc1.latitude - loc2.latitude)
        lng_diff = abs(loc1.longitude - loc2.longitude)
        return ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111
    
    async def get_job_history(self, limit: int = 50) -> List[Job]:
        """Get recent job history"""
        # Sort jobs by creation time, most recent first
        sorted_jobs = sorted(
            self.active_jobs.values(),
            key=lambda job: job.created_at,
            reverse=True
        )
        
        return sorted_jobs[:limit]
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get system analytics and metrics"""
        
        total_jobs = len(self.active_jobs)
        
        # Count jobs by status
        status_counts = {}
        for job in self.active_jobs.values():
            status = job.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count jobs by provider
        provider_counts = {}
        for job in self.active_jobs.values():
            provider = job.provider_id or "unknown"
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        # Count jobs by service type
        service_counts = {}
        for job in self.active_jobs.values():
            service = job.service_type.value
            service_counts[service] = service_counts.get(service, 0) + 1
        
        # Calculate average costs (simplified)
        completed_jobs = [j for j in self.active_jobs.values() if j.status == JobStatus.COMPLETED]
        avg_cost = 0
        if completed_jobs:
            costs = [float(job.actual_cost or job.estimated_cost or 0) for job in completed_jobs]
            avg_cost = sum(costs) / len(costs) if costs else 0
        
        # Provider health status
        provider_health = await self.router.get_provider_health_status()
        
        return {
            "total_jobs": total_jobs,
            "status_breakdown": status_counts,
            "provider_breakdown": provider_counts,
            "service_breakdown": service_counts,
            "average_cost_usd": round(avg_cost, 2),
            "active_providers": len([p for p, healthy in provider_health.items() if healthy]),
            "provider_health": provider_health,
            "total_quotes_cached": len(self.active_quotes)
        }
    
    async def cleanup_expired_quotes(self):
        """Remove expired quotes from cache"""
        current_time = datetime.utcnow()
        expired_quotes = [
            quote_id for quote_id, quote in self.active_quotes.items()
            if current_time > quote.expires_at
        ]
        
        for quote_id in expired_quotes:
            del self.active_quotes[quote_id]
        
        if expired_quotes:
            logger.info(f"Cleaned up {len(expired_quotes)} expired quotes")
    
    async def shutdown(self):
        """Clean shutdown of all provider connections"""
        logger.info("Shutting down Tesseracts Gateway...")
        
        shutdown_tasks = [provider.close() for provider in self.providers.values()]
        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        logger.info("Gateway shutdown complete")
