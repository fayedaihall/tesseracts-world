from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from .base import ProviderAdapter
from ..models.core import (
    Job, Quote, Worker, Location, ServiceType, 
    MovementRequest, JobUpdate, JobStatus
)

class UberAdapter(ProviderAdapter):
    """Adapter for Uber rideshare and delivery services"""
    
    def __init__(self, api_key: str):
        super().__init__(
            provider_id="uber",
            api_key=api_key,
            base_url="https://api.uber.com/v1"
        )
    
    @property
    def supported_service_types(self) -> List[ServiceType]:
        return [ServiceType.RIDESHARE, ServiceType.DELIVERY]
    
    @property
    def coverage_areas(self) -> List[str]:
        return ["global"]  # Uber operates globally
    
    async def get_quote(self, request: MovementRequest) -> Optional[Quote]:
        """Get quote from Uber API"""
        try:
            # Determine Uber product type based on service
            if request.service_type == ServiceType.RIDESHARE:
                endpoint = "/estimates/price"
                product_type = "uberX"  # Default to uberX
            else:  # DELIVERY
                endpoint = "/deliveries/quote"
                product_type = "uber_eats"
            
            params = {
                "start_latitude": request.pickup_location.latitude,
                "start_longitude": request.pickup_location.longitude,
                "end_latitude": request.dropoff_location.latitude,
                "end_longitude": request.dropoff_location.longitude,
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse Uber response (simplified - actual API structure may vary)
                if request.service_type == ServiceType.RIDESHARE:
                    prices = data.get("prices", [])
                    if prices:
                        price_info = prices[0]  # Take first available option
                        estimated_cost = Decimal(str(price_info.get("high_estimate", 0)))
                        duration = price_info.get("duration", 600)  # 10 min default
                else:
                    estimated_cost = Decimal(str(data.get("quote", {}).get("total", 0)))
                    duration = data.get("delivery_time_estimate", 1800)  # 30 min default
                
                pickup_time = request.requested_pickup_time or datetime.utcnow() + timedelta(minutes=5)
                delivery_time = pickup_time + timedelta(seconds=duration)
                
                return Quote(
                    provider_id=self.provider_id,
                    service_type=request.service_type,
                    estimated_cost=estimated_cost,
                    estimated_pickup_time=pickup_time,
                    estimated_delivery_time=delivery_time,
                    estimated_duration_minutes=duration // 60,
                    expires_at=datetime.utcnow() + timedelta(minutes=15),
                    quote_id=f"uber_{uuid.uuid4().hex[:8]}",
                    confidence_score=0.8
                )
            
        except Exception as e:
            print(f"Error getting Uber quote: {e}")
            return None
    
    async def create_job(self, quote_id: str, request: MovementRequest) -> Job:
        """Create job with Uber"""
        try:
            if request.service_type == ServiceType.RIDESHARE:
                endpoint = "/requests"
                payload = {
                    "start_latitude": request.pickup_location.latitude,
                    "start_longitude": request.pickup_location.longitude,
                    "end_latitude": request.dropoff_location.latitude,
                    "end_longitude": request.dropoff_location.longitude,
                    "product_id": "uberX"
                }
            else:  # DELIVERY
                endpoint = "/deliveries"
                payload = {
                    "pickup": {
                        "location": {
                            "latitude": request.pickup_location.latitude,
                            "longitude": request.pickup_location.longitude
                        }
                    },
                    "dropoff": {
                        "location": {
                            "latitude": request.dropoff_location.latitude,
                            "longitude": request.dropoff_location.longitude
                        }
                    }
                }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                uber_job_id = data.get("request_id") or data.get("delivery_id")
                
                return Job(
                    id=f"uber_{uber_job_id}",
                    service_type=request.service_type,
                    status=JobStatus.ASSIGNED,
                    pickup_location=request.pickup_location,
                    dropoff_location=request.dropoff_location,
                    provider_id=self.provider_id,
                    provider_job_id=uber_job_id,
                    requested_pickup_time=request.requested_pickup_time
                )
            else:
                raise Exception(f"Failed to create Uber job: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error creating Uber job: {e}")
    
    async def get_job_status(self, job_id: str) -> JobUpdate:
        """Get current job status from Uber"""
        try:
            # Extract Uber job ID from our job ID
            uber_job_id = job_id.replace("uber_", "")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.get(
                f"{self.base_url}/requests/{uber_job_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Map Uber status to our standard status
                uber_status = data.get("status", "unknown")
                status_mapping = {
                    "processing": JobStatus.PENDING,
                    "accepted": JobStatus.ASSIGNED,
                    "arriving": JobStatus.IN_PROGRESS,
                    "in_progress": JobStatus.IN_PROGRESS,
                    "completed": JobStatus.COMPLETED,
                    "cancelled": JobStatus.CANCELLED
                }
                
                status = status_mapping.get(uber_status, JobStatus.PENDING)
                
                # Extract location if available
                location = None
                if "location" in data:
                    loc_data = data["location"]
                    location = Location(
                        latitude=loc_data.get("latitude", 0),
                        longitude=loc_data.get("longitude", 0)
                    )
                
                return JobUpdate(
                    job_id=job_id,
                    status=status,
                    location=location,
                    message=data.get("status_message")
                )
            else:
                raise Exception(f"Failed to get Uber job status: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error getting Uber job status: {e}")
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel Uber job"""
        try:
            uber_job_id = job_id.replace("uber_", "")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.delete(
                f"{self.base_url}/requests/{uber_job_id}",
                headers=headers
            )
            
            return response.status_code in [200, 204]
            
        except Exception as e:
            print(f"Error cancelling Uber job: {e}")
            return False
    
    async def get_available_workers(self, location: Location, radius_km: float = 10.0) -> List[Worker]:
        """Get available Uber drivers/couriers near location"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            params = {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "radius": radius_km * 1000  # Convert to meters
            }
            
            response = await self.client.get(
                f"{self.base_url}/drivers",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                workers = []
                
                for driver_data in data.get("drivers", []):
                    worker = self._standardize_worker(driver_data)
                    workers.append(worker)
                
                return workers
            else:
                return []
                
        except Exception as e:
            print(f"Error getting Uber workers: {e}")
            return []
    
    async def track_job(self, job_id: str) -> Optional[Location]:
        """Track real-time location of Uber job"""
        try:
            job_update = await self.get_job_status(job_id)
            return job_update.location
        except Exception as e:
            print(f"Error tracking Uber job: {e}")
            return None
