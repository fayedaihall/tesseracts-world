from sqlalchemy import Column, String, Float, Integer, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class SellerDB(Base):
    __tablename__ = "sellers"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    did_method = Column(String, default="did:key")
    did_identifier = Column(String, nullable=False)
    website = Column(String)
    contact_email = Column(String)
    reputation_score = Column(Float, default=0.0)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    products = relationship("ProductDB", back_populates="seller")
    orders = relationship("OrderDB", back_populates="seller")

class ProductDB(Base):
    __tablename__ = "products"
    
    id = Column(String, primary_key=True)
    seller_id = Column(String, ForeignKey("sellers.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    sku = Column(String)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    weight_kg = Column(Float)
    dimensions_cm = Column(JSON)
    categories = Column(JSON, default=list)
    images = Column(JSON, default=list)
    inventory = Column(Integer, default=0)
    fulfillment_origin = Column(JSON, default=dict)
    attributes = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # External federation fields
    external_id = Column(String)
    external_source = Column(String)  # Source marketplace/feed
    external_url = Column(String)
    
    # Relationships
    seller = relationship("SellerDB", back_populates="products")
    order_items = relationship("OrderItemDB", back_populates="product")

class OrderDB(Base):
    __tablename__ = "orders"
    
    id = Column(String, primary_key=True)
    buyer_did_method = Column(String, default="did:key")
    buyer_did_identifier = Column(String, nullable=False)
    seller_id = Column(String, ForeignKey("sellers.id"), nullable=False)
    subtotal = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    delivery_fee = Column(Float, default=0.0)
    total = Column(Float, nullable=False)
    status = Column(String, default="pending")
    
    # Payment/escrow info
    payment_id = Column(String)
    payment_method = Column(String)
    payment_amount = Column(Float)
    escrow_status = Column(String)
    escrow_reference = Column(String)  # Flow transaction ID
    flow_escrow_id = Column(String)
    
    # Addresses
    pickup_name = Column(String)
    pickup_phone = Column(String)
    pickup_address = Column(String)
    pickup_latitude = Column(Float, nullable=False)
    pickup_longitude = Column(Float, nullable=False)
    
    dropoff_name = Column(String)
    dropoff_phone = Column(String)
    dropoff_address = Column(String)
    dropoff_latitude = Column(Float, nullable=False)
    dropoff_longitude = Column(Float, nullable=False)
    
    # Movement integration
    movement_request_id = Column(String)
    movement_job_id = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    seller = relationship("SellerDB", back_populates="orders")
    items = relationship("OrderItemDB", back_populates="order", cascade="all, delete-orphan")

class OrderItemDB(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    title = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    weight_kg = Column(Float)
    
    # Relationships
    order = relationship("OrderDB", back_populates="items")
    product = relationship("ProductDB", back_populates="order_items")

class ExternalFeedDB(Base):
    __tablename__ = "external_feeds"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    feed_type = Column(String, default="json")  # json, rss, csv, etc.
    last_fetched = Column(DateTime)
    last_success = Column(DateTime)
    status = Column(String, default="active")
    config = Column(JSON, default=dict)  # Feed-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
