from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import random
from .base import ProviderAdapter
from ..models.core import (
    Job, Quote, Worker, Location, ServiceType, 
    MovementRequest, JobUpdate, JobStatus, Vehicle
)

class MockLocalAdapter(ProviderAdapter):
    """Mock adapter for local gig workers - useful for testing and demonstration"""
    
    def __init__(self, provider_name: str = "LocalGig"):
        super().__init__(
            provider_id=f"local_{provider_name.lower()}",
            api_key="mock_key",
            base_url="http://localhost:8001"  # Mock endpoint
        )
        self.provider_name = provider_name
        
        # Simulate some workers
        self.mock_workers = self._generate_mock_workers()
        self.active_jobs: Dict[str, Job] = {}
    
    @property
    def supported_service_types(self) -> List[ServiceType]:
        return [ServiceType.DELIVERY, ServiceType.COURIER, ServiceType.GIG_WORK]
    
    @property
    def coverage_areas(self) -> List[str]:
        return ["local", "city"]
    
    def _generate_mock_workers(self) -> List[Worker]:
        """Generate mock workers for demonstration"""
        workers = []
        vehicle_types = ["bike", "car", "scooter", "walking"]
        
        for i in range(10):
            vehicle_type = random.choice(vehicle_types)
            
            worker = Worker(
                id=f"{self.provider_id}_worker_{i}",
                name=f"Worker {i+1}",
                phone=f"+1555000{i:04d}",
                rating=round(random.uniform(3.5, 5.0), 1),
                vehicle=Vehicle(
                    type=vehicle_type,
                    capacity_kg=50 if vehicle_type == "car" else 15,
                    license_plate=f"LOC{i:03d}" if vehicle_type == "car" else None
                ),
                current_location=Location(
                    latitude=37.7749 + random.uniform(-0.1, 0.1),  # San Francisco area
                    longitude=-122.4194 + random.uniform(-0.1, 0.1)
                ),
                is_available=random.choice([True, True, True, False]),  # 75% available
                provider_id=self.provider_id,
                provider_worker_id=f"worker_{i}"
            )
            workers.append(worker)
        
        return workers
    
    async def get_quote(self, request: MovementRequest) -> Optional[Quote]:
        """Get quote from mock local provider"""
        try:
            # Calculate distance-based pricing
            lat_diff = abs(request.pickup_location.latitude - request.dropoff_location.latitude)
            lng_diff = abs(request.pickup_location.longitude - request.dropoff_location.longitude)
            estimated_distance = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111  # Rough km conversion
            
            # Base pricing model
            base_cost = Decimal("5.00")
            distance_cost = Decimal(str(estimated_distance * 2.5))
            priority_multiplier = {
                "low": 0.8,
                "normal": 1.0,
                "high": 1.3,
                "urgent": 1.8
            }
            
            estimated_cost = (base_cost + distance_cost) * Decimal(str(priority_multiplier[request.priority]))
            
            # Estimate timing
            duration_minutes = max(int(estimated_distance * 3), 10)  # 3 min per km minimum 10
            pickup_delay = 5 if request.priority == "urgent" else 15
            
            pickup_time = request.requested_pickup_time or datetime.utcnow() + timedelta(minutes=pickup_delay)
            delivery_time = pickup_time + timedelta(minutes=duration_minutes)
            
            # Find available worker
            available_workers = [w for w in self.mock_workers if w.is_available]
            worker_info = random.choice(available_workers) if available_workers else None
            
            return Quote(
                provider_id=self.provider_id,
                service_type=request.service_type,
                estimated_cost=estimated_cost,
                estimated_pickup_time=pickup_time,
                estimated_delivery_time=delivery_time,
                estimated_duration_minutes=duration_minutes,
                worker_info=worker_info,
                expires_at=datetime.utcnow() + timedelta(minutes=20),
                quote_id=f"{self.provider_id}_{uuid.uuid4().hex[:8]}",
                confidence_score=0.9
            )
            
        except Exception as e:
            print(f"Error getting {self.provider_name} quote: {e}")
            return None
    
    async def create_job(self, quote_id: str, request: MovementRequest) -> Job:
        """Create job with mock local provider"""
        try:
            job_id = f"{self.provider_id}_{uuid.uuid4().hex[:8]}"
            
            # Assign a worker
            available_workers = [w for w in self.mock_workers if w.is_available]
            assigned_worker = random.choice(available_workers) if available_workers else None
            
            if assigned_worker:
                # Mark worker as unavailable
                for worker in self.mock_workers:
                    if worker.id == assigned_worker.id:
                        worker.is_available = False
                        break
            
            job = Job(
                id=job_id,
                service_type=request.service_type,
                status=JobStatus.ASSIGNED if assigned_worker else JobStatus.PENDING,
                pickup_location=request.pickup_location,
                dropoff_location=request.dropoff_location,
                assigned_worker=assigned_worker,
                provider_id=self.provider_id,
                provider_job_id=job_id,
                requested_pickup_time=request.requested_pickup_time,
                description=request.special_requirements.get("description") if request.special_requirements else None
            )
            
            self.active_jobs[job_id] = job
            return job
            
        except Exception as e:
            raise Exception(f"Error creating {self.provider_name} job: {e}")
    
    async def get_job_status(self, job_id: str) -> JobUpdate:
        """Get current job status from mock provider"""
        try:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                
                # Simulate job progression
                current_time = datetime.utcnow()
                
                if job.status == JobStatus.ASSIGNED:
                    # Check if pickup time has passed
                    if job.requested_pickup_time and current_time >= job.requested_pickup_time:
                        job.status = JobStatus.IN_PROGRESS
                        job.actual_pickup_time = current_time
                
                elif job.status == JobStatus.IN_PROGRESS:
                    # Check if delivery should be completed
                    if job.actual_pickup_time:
                        estimated_completion = job.actual_pickup_time + timedelta(minutes=30)
                        if current_time >= estimated_completion:
                            job.status = JobStatus.COMPLETED
                            job.actual_delivery_time = current_time
                            
                            # Free up the worker
                            if job.assigned_worker:
                                for worker in self.mock_workers:
                                    if worker.id == job.assigned_worker.id:
                                        worker.is_available = True
                                        break
                
                # Get worker location if assigned
                location = None
                if job.assigned_worker and job.status == JobStatus.IN_PROGRESS:
                    # Simulate movement between pickup and dropoff
                    pickup = job.pickup_location
                    dropoff = job.dropoff_location
                    
                    # Linear interpolation based on time elapsed
                    if job.actual_pickup_time:
                        elapsed = (current_time - job.actual_pickup_time).total_seconds()
                        total_duration = 30 * 60  # 30 minutes
                        progress = min(elapsed / total_duration, 1.0)
                        
                        lat = pickup.latitude + (dropoff.latitude - pickup.latitude) * progress
                        lng = pickup.longitude + (dropoff.longitude - pickup.longitude) * progress
                        
                        location = Location(latitude=lat, longitude=lng)
                
                return JobUpdate(
                    job_id=job_id,
                    status=job.status,
                    location=location,
                    message=f"Job {job.status.value} with {self.provider_name}"
                )
            else:
                raise Exception(f"Job {job_id} not found")
                
        except Exception as e:
            raise Exception(f"Error getting {self.provider_name} job status: {e}")
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel mock provider job"""
        try:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.status = JobStatus.CANCELLED
                
                # Free up the worker
                if job.assigned_worker:
                    for worker in self.mock_workers:
                        if worker.id == job.assigned_worker.id:
                            worker.is_available = True
                            break
                
                return True
            return False
            
        except Exception as e:
            print(f"Error cancelling {self.provider_name} job: {e}")
            return False
    
    async def get_available_workers(self, location: Location, radius_km: float = 10.0) -> List[Worker]:
        """Get available workers near location"""
        try:
            available_workers = []
            
            for worker in self.mock_workers:
                if not worker.is_available or not worker.current_location:
                    continue
                
                # Calculate distance (simplified)
                lat_diff = abs(worker.current_location.latitude - location.latitude)
                lng_diff = abs(worker.current_location.longitude - location.longitude)
                distance_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111
                
                if distance_km <= radius_km:
                    available_workers.append(worker)
            
            return available_workers
            
        except Exception as e:
            print(f"Error getting {self.provider_name} workers: {e}")
            return []
    
    async def track_job(self, job_id: str) -> Optional[Location]:
        """Track real-time location of mock job"""
        try:
            job_update = await self.get_job_status(job_id)
            return job_update.location
        except Exception as e:
            print(f"Error tracking {self.provider_name} job: {e}")
            return None
