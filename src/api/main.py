from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

from ..core.gateway import TesseractsGateway
from ..core.commerce import get_catalog_service, get_order_service, get_payment_service
from ..adapters.uber import UberAdapter
from ..adapters.mock_local import MockLocalAdapter
from ..adapters.flow_escrow import flow_escrow_adapter
from ..models.core import MovementRequest, ServiceType, Location, Priority, JobStatus
from ..models.commerce import Seller, Product, Order, OrderItem, Address, DecentralizedIdentity
from ..services.federation import federation_service
from ..database import db_manager
from ..config.settings import settings

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
    
    # Initialize database
    await db_manager.initialize()
    
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

# === COMMERCE ENDPOINTS ===

# Seller management
@app.post(f"{settings.api_prefix}/sellers")
async def register_seller(seller: Seller, api_key: str = Depends(verify_api_key)):
    """Register a new seller"""
    try:
        catalog_service = get_catalog_service()
        registered_seller = await catalog_service.register_seller(seller)
        return registered_seller
    except Exception as e:
        logger.error(f"Error registering seller: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/sellers/{{seller_id}}")
async def get_seller(seller_id: str, api_key: str = Depends(verify_api_key)):
    """Get seller details"""
    try:
        catalog_service = get_catalog_service()
        seller = await catalog_service.get_seller(seller_id)
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
        return seller
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting seller: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Product management
@app.post(f"{settings.api_prefix}/products")
async def publish_product(product: Product, api_key: str = Depends(verify_api_key)):
    """Publish a new product"""
    try:
        catalog_service = get_catalog_service()
        published_product = await catalog_service.publish_product(product)
        return published_product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error publishing product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/products/{{product_id}}")
async def get_product(product_id: str, api_key: str = Depends(verify_api_key)):
    """Get product details"""
    try:
        catalog_service = get_catalog_service()
        product = await catalog_service.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/products")
async def list_products(
    seller_id: str = None,
    skip: int = 0,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """List products"""
    try:
        catalog_service = get_catalog_service()
        products = await catalog_service.list_products(seller_id, skip, limit)
        return {"products": products, "count": len(products)}
    except Exception as e:
        logger.error(f"Error listing products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/products/search")
async def search_products(
    q: str = "",
    categories: List[str] = [],
    min_price: float = None,
    max_price: float = None,
    skip: int = 0,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """Search products"""
    try:
        catalog_service = get_catalog_service()
        products = await catalog_service.search(
            query=q,
            categories=categories if categories else None,
            min_price=min_price,
            max_price=max_price,
            skip=skip,
            limit=limit
        )
        return {"products": products, "query": q, "count": len(products)}
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Order management
@app.post(f"{settings.api_prefix}/orders")
async def create_order(
    request: Dict[str, Any],  # {seller_id, items, dropoff, buyer_did_identifier}
    api_key: str = Depends(verify_api_key)
):
    """Create a new order"""
    try:
        order_service = get_order_service(gateway)
        
        # Parse request
        seller_id = request["seller_id"]
        items_data = request["items"]
        dropoff_data = request["dropoff"]
        buyer_did = request["buyer_did_identifier"]
        
        # Create order items
        items = [OrderItem(**item) for item in items_data]
        dropoff = Address(**dropoff_data)
        
        order = await order_service.create_order(seller_id, items, dropoff, buyer_did)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/orders/{{order_id}}")
async def get_order(order_id: str, api_key: str = Depends(verify_api_key)):
    """Get order details"""
    try:
        order_service = get_order_service(gateway)
        order = await order_service.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.api_prefix}/orders/{{order_id}}/delivery/quotes")
async def request_delivery_quotes(order_id: str, api_key: str = Depends(verify_api_key)):
    """Request delivery quotes for order"""
    try:
        order_service = get_order_service(gateway)
        quotes = await order_service.request_delivery_quotes(order_id)
        return quotes
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error requesting delivery quotes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.api_prefix}/orders/{{order_id}}/delivery/accept")
async def accept_delivery_quote(
    order_id: str,
    request: Dict[str, str],  # {quote_id}
    api_key: str = Depends(verify_api_key)
):
    """Accept delivery quote and book delivery"""
    try:
        order_service = get_order_service(gateway)
        quote_id = request["quote_id"]
        job = await order_service.accept_delivery_and_book(order_id, quote_id)
        return job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error accepting delivery quote: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Escrow/Payment endpoints
@app.post(f"{settings.api_prefix}/orders/{{order_id}}/escrow")
async def create_escrow(
    order_id: str,
    request: Dict[str, Any],  # {amount, currency}
    api_key: str = Depends(verify_api_key)
):
    """Create escrow for order"""
    try:
        amount = request["amount"]
        currency = request.get("currency", "USD")
        
        escrow_result = await flow_escrow_adapter.create_escrow(
            amount, currency, {"order_id": order_id}
        )
        return escrow_result
    except Exception as e:
        logger.error(f"Error creating escrow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.api_prefix}/orders/{{order_id}}/escrow/fund")
async def fund_escrow(
    order_id: str,
    request: Dict[str, str],  # {escrow_id}
    api_key: str = Depends(verify_api_key)
):
    """Fund escrow for order"""
    try:
        escrow_id = request["escrow_id"]
        result = await flow_escrow_adapter.fund_escrow(escrow_id)
        return result
    except Exception as e:
        logger.error(f"Error funding escrow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.api_prefix}/orders/{{order_id}}/escrow/release")
async def release_escrow(
    order_id: str,
    request: Dict[str, str],  # {escrow_id}
    api_key: str = Depends(verify_api_key)
):
    """Release escrow for completed order"""
    try:
        escrow_id = request["escrow_id"]
        result = await flow_escrow_adapter.release_escrow(escrow_id)
        return result
    except Exception as e:
        logger.error(f"Error releasing escrow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === FEDERATION ENDPOINTS ===

@app.post(f"{settings.api_prefix}/federation/feeds")
async def register_feed(
    request: Dict[str, Any],  # {name, url, feed_type, config}
    api_key: str = Depends(verify_api_key)
):
    """Register external catalog feed"""
    try:
        feed_id = await federation_service.register_feed(
            name=request["name"],
            url=request["url"],
            feed_type=request.get("feed_type", "json"),
            config=request.get("config", {})
        )
        return {"feed_id": feed_id, "status": "registered"}
    except Exception as e:
        logger.error(f"Error registering feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/federation/feeds")
async def list_feeds(api_key: str = Depends(verify_api_key)):
    """List all registered feeds"""
    try:
        feeds = await federation_service.list_feeds()
        return {"feeds": feeds, "count": len(feeds)}
    except Exception as e:
        logger.error(f"Error listing feeds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.api_prefix}/federation/feeds/{{feed_id}}/ingest")
async def ingest_feed(
    feed_id: str,
    seller_id: str = None,
    api_key: str = Depends(verify_api_key)
):
    """Manually trigger feed ingestion"""
    try:
        result = await federation_service.ingest_feed(feed_id, seller_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error ingesting feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.api_prefix}/federation/ingest-all")
async def ingest_all_feeds(api_key: str = Depends(verify_api_key)):
    """Ingest all active feeds"""
    try:
        results = await federation_service.ingest_all_feeds()
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error ingesting all feeds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
