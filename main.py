from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
import json
import logging
from typing import List, Dict, Any
from datetime import datetime
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.gateway import TesseractsGateway
from src.adapters.uber import UberAdapter
from src.adapters.mock_local import MockLocalAdapter
from src.core.commerce import get_catalog_service, get_order_service, get_payment_service
from src.models.commerce import Seller, Product, OrderItem, Address, PaymentMethod
from src.models.core import MovementRequest, ServiceType, Location, Priority, JobStatus
from config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="The Universal API for Movement - Route anything, anywhere through the gig economy",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize providers and gateway
providers = [
    MockLocalAdapter("QuickGig"),
    MockLocalAdapter("CityRunners"),
    MockLocalAdapter("LocalCouriers"),
]

# Add real providers if API keys are available
if settings.uber_api_key:
    providers.append(UberAdapter(settings.uber_api_key))

gateway = TesseractsGateway(providers)

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple API key verification - in production, this would be more sophisticated"""
    # For demo purposes, accept any non-empty token
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

@app.on_event("startup")
async def startup_event():
    """Initialize background tasks"""
    logger.info("Starting Tesseracts World API...")
    
    # Start background task to cleanup expired quotes
    asyncio.create_task(cleanup_quotes_task())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    await gateway.shutdown()

async def cleanup_quotes_task():
    """Background task to cleanup expired quotes"""
    while True:
        try:
            await gateway.cleanup_expired_quotes()
            await asyncio.sleep(300)  # Run every 5 minutes
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60)

# REST API Endpoints

# Commerce: Sellers
@app.post(f"{settings.api_prefix}/commerce/sellers")
async def register_seller(seller: Seller, api_key: str = Depends(verify_api_key)):
    return get_catalog_service().register_seller(seller)

# Commerce: Products
@app.post(f"{settings.api_prefix}/commerce/products")
async def publish_product(product: Product, api_key: str = Depends(verify_api_key)):
    return get_catalog_service().publish_product(product)

@app.get(f"{settings.api_prefix}/commerce/products")
async def list_products(seller_id: str | None = None, api_key: str = Depends(verify_api_key)):
    return get_catalog_service().list_products(seller_id)

@app.get(f"{settings.api_prefix}/commerce/search")
async def search_products(q: str = "", category: list[str] | None = None, api_key: str = Depends(verify_api_key)):
    return get_catalog_service().search(q, category)

# Commerce: Orders
class CreateOrderRequest(MovementRequest):
    seller_id: str
    items: list[OrderItem]
    dropoff: Address

@app.post(f"{settings.api_prefix}/commerce/orders")
async def create_order(payload: CreateOrderRequest, api_key: str = Depends(verify_api_key)):
    try:
        order_service = get_order_service(gateway)
        order = order_service.create_order(
            seller_id=payload.seller_id,
            items=payload.items,
            dropoff=payload.dropoff,
        )
        # Initiate escrow (mock)
        payment_svc = get_payment_service()
        payment = payment_svc.initiate_crypto_escrow(amount=order.total, currency=order.currency)
        order.payment = payment
        order.status = order.status.PAYMENT_PENDING
        # Request movement quotes tied to order
        quotes = await order_service.request_delivery_quotes(order.id)
        return {"order": order, "delivery_quotes": quotes}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post(f"{settings.api_prefix}/commerce/orders/{{order_id}}/fund")
async def fund_order_escrow(order_id: str, api_key: str = Depends(verify_api_key)):
    order = get_order_service(gateway).orders.get(order_id)
    if not order or not order.payment:
        raise HTTPException(status_code=404, detail="Order or payment not found")
    payment = get_payment_service().fund_escrow(order.payment)
    order.payment = payment
    order.status = order.status.PAID
    order.updated_at = datetime.utcnow()
    return {"order": order}

@app.post(f"{settings.api_prefix}/commerce/orders/{{order_id}}/accept")
async def accept_order_delivery(order_id: str, quote_id: str, api_key: str = Depends(verify_api_key)):
    try:
        order_service = get_order_service(gateway)
        job = await order_service.accept_delivery_and_book(order_id, quote_id)
        # Reduce inventory after dispatch
        order_service.reduce_inventory(order_id)
        return {"job": job, "order": order_service.orders.get(order_id)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post(f"{settings.api_prefix}/commerce/orders/{{order_id}}/release")
async def release_order_escrow(order_id: str, api_key: str = Depends(verify_api_key)):
    order = get_order_service(gateway).orders.get(order_id)
    if not order or not order.payment:
        raise HTTPException(status_code=404, detail="Order or payment not found")
    payment = get_payment_service().release_escrow(order.payment)
    order.payment = payment
    order.updated_at = datetime.utcnow()
    return {"order": order}

# Existing movement endpoints

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to Tesseracts World - The Universal API for Movement",
        "version": settings.app_version,
        "documentation": "/docs"
    }

@app.post(f"{settings.api_prefix}/movement/request")
async def request_movement(
    request: MovementRequest,
    api_key: str = Depends(verify_api_key)
):
    """Request movement quotes from all available providers"""
    try:
        response = await gateway.request_movement(request)
        return response
    except Exception as e:
        logger.error(f"Error processing movement request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.api_prefix}/movement/accept")
async def accept_quote(
    quote_id: str,
    request: MovementRequest,
    api_key: str = Depends(verify_api_key)
):
    """Accept a quote and create a job"""
    try:
        job = await gateway.accept_quote(quote_id, request)
        
        # Broadcast job creation to WebSocket clients
        await manager.broadcast(json.dumps({
            "type": "job_created",
            "job_id": job.id,
            "status": job.status.value,
            "provider": job.provider_id
        }))
        
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error accepting quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/jobs/{{job_id}}/status")
async def get_job_status(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get current status of a job"""
    try:
        job_update = await gateway.get_job_status(job_id)
        return job_update
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(f"{settings.api_prefix}/jobs/{{job_id}}")
async def cancel_job(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Cancel a job"""
    try:
        success = await gateway.cancel_job(job_id)
        
        if success:
            # Broadcast cancellation to WebSocket clients
            await manager.broadcast(json.dumps({
                "type": "job_cancelled",
                "job_id": job_id
            }))
            
            return {"success": True, "message": f"Job {job_id} cancelled"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel job")
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/jobs/{{job_id}}/track")
async def track_job(
    job_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get real-time location of a job"""
    try:
        location = await gateway.track_job(job_id)
        return {"job_id": job_id, "location": location}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error tracking job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/workers")
async def get_available_workers(
    latitude: float,
    longitude: float,
    service_type: ServiceType,
    radius_km: float = 10.0,
    api_key: str = Depends(verify_api_key)
):
    """Get available workers near a location"""
    try:
        location = Location(latitude=latitude, longitude=longitude)
        workers = await gateway.get_available_workers(location, service_type, radius_km)
        return {"workers": workers, "count": len(workers)}
    except Exception as e:
        logger.error(f"Error getting available workers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/jobs")
async def get_job_history(
    limit: int = 50,
    api_key: str = Depends(verify_api_key)
):
    """Get job history"""
    try:
        jobs = await gateway.get_job_history(limit)
        return {"jobs": jobs, "count": len(jobs)}
    except Exception as e:
        logger.error(f"Error getting job history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/analytics")
async def get_analytics(api_key: str = Depends(verify_api_key)):
    """Get system analytics and metrics"""
    try:
        analytics = await gateway.get_analytics()
        return analytics
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/health")
async def health_check():
    """System health check"""
    try:
        provider_health = await gateway.router.get_provider_health_status()
        healthy_providers = sum(1 for healthy in provider_health.values() if healthy)
        
        return {
            "status": "healthy" if healthy_providers > 0 else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "providers": provider_health,
            "healthy_providers": healthy_providers,
            "total_providers": len(provider_health)
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# WebSocket endpoint for real-time updates
@app.websocket(f"{settings.api_prefix}/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time job updates"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "subscribe_job":
                    job_id = message.get("job_id")
                    if job_id:
                        # Start tracking this job and send updates
                        asyncio.create_task(track_job_updates(websocket, job_id))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def track_job_updates(websocket: WebSocket, job_id: str):
    """Background task to send job updates via WebSocket"""
    previous_status = None
    previous_location = None
    
    while True:
        try:
            # Get current job status
            job_update = await gateway.get_job_status(job_id)
            
            # Send update if status or location changed
            if (job_update.status != previous_status or 
                job_update.location != previous_location):
                
                await websocket.send_text(json.dumps({
                    "type": "job_update",
                    "job_id": job_id,
                    "status": job_update.status.value,
                    "location": {
                        "latitude": job_update.location.latitude,
                        "longitude": job_update.location.longitude
                    } if job_update.location else None,
                    "message": job_update.message,
                    "timestamp": job_update.timestamp.isoformat()
                }))
                
                previous_status = job_update.status
                previous_location = job_update.location
            
            # Stop tracking if job is completed or cancelled
            if job_update.status in [JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED]:
                break
            
            await asyncio.sleep(10)  # Update every 10 seconds
            
        except Exception as e:
            logger.error(f"Error tracking job {job_id}: {e}")
            break

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
