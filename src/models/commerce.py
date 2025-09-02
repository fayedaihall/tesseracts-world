from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import uuid4

class DID(BaseModel):
    method: str = "did:key"
    identifier: str = Field(default_factory=lambda: uuid4().hex)

class Seller(BaseModel):
    id: str = Field(default_factory=lambda: f"seller_{uuid4().hex[:8]}")
    name: str
    did: DID = Field(default_factory=DID)
    website: Optional[str] = None
    contact_email: Optional[str] = None
    reputation_score: float = 0.0  # Placeholder for on-chain / off-chain reputation
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: f"prod_{uuid4().hex[:8]}")
    seller_id: str
    title: str
    description: Optional[str] = None
    sku: Optional[str] = None
    price: float
    currency: str = "USD"
    weight_kg: Optional[float] = None
    dimensions_cm: Optional[Dict[str, float]] = None
    categories: List[str] = []
    images: List[str] = []
    inventory: int = 0
    fulfillment_origin: Dict[str, Any] = {}  # {latitude, longitude, address}
    attributes: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    FULFILLING = "fulfilling"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(str, Enum):
    CRYPTO = "crypto"
    CARD = "card"
    OTHER = "other"

class EscrowStatus(str, Enum):
    INITIATED = "initiated"
    FUNDED = "funded"
    RELEASED = "released"
    DISPUTED = "disputed"
    REFUNDED = "refunded"

class Payment(BaseModel):
    id: str = Field(default_factory=lambda: f"pay_{uuid4().hex[:8]}")
    method: PaymentMethod
    amount: float
    currency: str = "USD"
    escrow_status: Optional[EscrowStatus] = None
    reference: Optional[str] = None  # tx hash or PSP ref
    created_at: datetime = Field(default_factory=datetime.utcnow)

class OrderItem(BaseModel):
    product_id: str
    title: str
    quantity: int
    unit_price: float
    currency: str
    weight_kg: Optional[float] = None

class Address(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    latitude: float
    longitude: float

class Order(BaseModel):
    id: str = Field(default_factory=lambda: f"ord_{uuid4().hex[:8]}")
    buyer_did: DID = Field(default_factory=DID)
    seller_id: str
    items: List[OrderItem]
    subtotal: float
    currency: str = "USD"
    delivery_fee: float = 0.0
    total: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    payment: Optional[Payment] = None
    pickup: Address
    dropoff: Address
    movement_request_id: Optional[str] = None
    movement_job_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

