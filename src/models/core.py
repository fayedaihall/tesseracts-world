from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal

class ServiceType(str, Enum):
    RIDESHARE = "rideshare"
    DELIVERY = "delivery"
    COURIER = "courier"
    FREIGHT = "freight"
    GIG_WORK = "gig_work"

class JobStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

class Vehicle(BaseModel):
    type: str  # car, bike, scooter, truck, van, walking
    capacity_kg: Optional[float] = None
    capacity_cubic_meters: Optional[float] = None
    license_plate: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None

class Worker(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    vehicle: Optional[Vehicle] = None
    current_location: Optional[Location] = None
    is_available: bool = True
    provider_id: str
    provider_worker_id: str

class Route(BaseModel):
    origin: Location
    destination: Location
    waypoints: List[Location] = []
    estimated_distance_km: Optional[float] = None
    estimated_duration_minutes: Optional[int] = None
    estimated_cost: Optional[Decimal] = None

class Job(BaseModel):
    id: str
    service_type: ServiceType
    status: JobStatus = JobStatus.PENDING
    priority: Priority = Priority.NORMAL
    
    # Location and routing
    pickup_location: Location
    dropoff_location: Location
    route: Optional[Route] = None
    
    # Timing
    requested_pickup_time: Optional[datetime] = None
    actual_pickup_time: Optional[datetime] = None
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    
    # Assignment
    assigned_worker: Optional[Worker] = None
    provider_id: Optional[str] = None
    provider_job_id: Optional[str] = None
    
    # Job details
    description: Optional[str] = None
    special_instructions: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    
    # Package/cargo details (for deliveries)
    package_weight_kg: Optional[float] = None
    package_dimensions: Optional[Dict[str, float]] = None  # length, width, height
    package_value: Optional[Decimal] = None
    fragile: bool = False
    
    # Pricing
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    currency: str = "USD"
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}

class Provider(BaseModel):
    id: str
    name: str
    service_types: List[ServiceType]
    coverage_areas: List[str]  # Geographic areas served
    api_endpoint: str
    is_active: bool = True
    supports_real_time_tracking: bool = False
    supports_scheduling: bool = False
    min_advance_booking_minutes: int = 0
    max_advance_booking_hours: int = 24
    
class Quote(BaseModel):
    provider_id: str
    service_type: ServiceType
    estimated_cost: Decimal
    estimated_pickup_time: datetime
    estimated_delivery_time: datetime
    estimated_duration_minutes: int
    worker_info: Optional[Worker] = None
    expires_at: datetime
    quote_id: str
    confidence_score: float = Field(ge=0, le=1)  # How confident we are in this quote

class MovementRequest(BaseModel):
    service_type: ServiceType
    pickup_location: Location
    dropoff_location: Location
    requested_pickup_time: Optional[datetime] = None
    priority: Priority = Priority.NORMAL
    special_requirements: Optional[Dict[str, Any]] = None
    contact_info: Optional[Dict[str, str]] = None
    package_details: Optional[Dict[str, Any]] = None
    
class MovementResponse(BaseModel):
    request_id: str
    quotes: List[Quote]
    recommended_quote_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class JobUpdate(BaseModel):
    job_id: str
    status: JobStatus
    location: Optional[Location] = None
    estimated_arrival: Optional[datetime] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
