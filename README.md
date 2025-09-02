# Tesseracts World - The Universal API for Movement

![Tesseracts World Logo](https://via.placeholder.com/300x100/4A90E2/FFFFFF?text=Tesseracts+World)

> **"The Plaid for the gig economy, ride shares, and deliveries"**

Tesseracts World is a universal API that connects fragmented movement and logistics services, enabling developers to route anything, anywhere through a single integration. Just as Plaid revolutionized fintech by connecting banks and financial services, Tesseracts World revolutionizes logistics by connecting rideshare, delivery, and gig work providers.

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/tesseracts-world/api
cd tesseracts-world
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run the API

```bash
python -m src.api.main
```

The API will be available at `http://localhost:8000` with interactive documentation at `/docs`.

### Your First Request

```python
import httpx

# Request delivery quotes
response = httpx.post("http://localhost:8000/api/v1/movement/request", 
    headers={"Authorization": "Bearer tesseracts_demo_key_12345"},
    json={
        "service_type": "delivery",
        "pickup_location": {"latitude": 37.7749, "longitude": -122.4194},
        "dropoff_location": {"latitude": 37.7849, "longitude": -122.4094},
        "priority": "normal"
    }
)

quotes = response.json()["quotes"]
print(f"Found {len(quotes)} delivery options!")
```

## 🌟 Features

### Universal Movement API
- **One Integration, Global Access**: Connect once to access rideshare, delivery, courier, and gig work services worldwide
- **Intelligent Routing**: AI-powered selection of optimal providers based on cost, time, reliability, and quality
- **Real-time Tracking**: WebSocket-based live updates for job status and location tracking
- **Multi-modal Support**: Handle rideshares, deliveries, courier services, freight, and gig work through unified interfaces

### Developer Experience
- **RESTful API**: Clean, well-documented REST endpoints
- **Real-time Updates**: WebSocket support for live job tracking
- **SDK Libraries**: Python, JavaScript, and other language bindings
- **Comprehensive Documentation**: Interactive API docs, integration guides, and examples

### Enterprise Features
- **Rate Limiting**: Configurable API rate limits per client
- **Authentication**: Secure API key management with JWT token support
- **Analytics**: Detailed metrics and reporting on usage and performance
- **High Availability**: Built for scale with async processing and provider failover

## 📋 Use Cases

### 1. Rideshare Aggregation
Perfect for hotels, travel apps, and event platforms:

```python
from examples.rideshare_aggregator import RideshareAggregator

aggregator = RideshareAggregator("your_api_key")

# Find rides from hotel to airport
rides = await aggregator.find_rides(
    pickup_lat=37.7749, pickup_lng=-122.4194,  # Hotel
    dropoff_lat=37.6213, dropoff_lng=-122.3790  # Airport
)

# Book the best option
booking = await aggregator.book_ride(rides[0]["quote_id"], ...)
```

### 2. Delivery Orchestration
Ideal for e-commerce, restaurants, and marketplaces:

```python
from examples.delivery_orchestrator import DeliveryOrchestrator

orchestrator = DeliveryOrchestrator("your_api_key")

# Find fastest delivery options
options = await orchestrator.find_fastest_delivery(
    pickup_lat=warehouse_lat, pickup_lng=warehouse_lng,
    dropoff_lat=customer_lat, dropoff_lng=customer_lng,
    package_weight_kg=2.5
)

# Schedule delivery
delivery = await orchestrator.schedule_delivery(options[0]["quote_id"], ...)
```

### 3. Gig Worker Marketplace
Enable workers to access multiple job sources:

```python
# Find available gig work near a location
workers = await client.get("/api/v1/workers", params={
    "latitude": 37.7749,
    "longitude": -122.4194,
    "service_type": "gig_work",
    "radius_km": 15
})
```

### 4. Multi-Modal Transport Planning
Coordinate complex logistics operations:

```python
# Plan multi-stop delivery route
stops = [warehouse, store_a, store_b, customer]
optimized_route = await gateway.router.optimize_multi_stop_route(
    stops, ServiceType.DELIVERY
)
```

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │    │  Tesseracts API  │    │   Provider      │
│                 │    │                  │    │   Adapters      │
│ • Hotel Apps    │────│ • Route Optimizer│────│ • Uber          │
│ • E-commerce    │    │ • Job Tracking   │    │ • DoorDash      │
│ • Marketplaces  │    │ • Real-time WS   │    │ • Local Couriers│
│ • Event Platforms│   │ • Authentication │    │ • Custom APIs   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Provider Adapter System
Tesseracts World uses a standardized adapter pattern to integrate with different gig economy providers:

- **Base Adapter Interface**: Standardized methods for quotes, job creation, tracking, and cancellation
- **Provider-Specific Implementations**: Adapters for Uber, Lyft, DoorDash, Instacart, local providers, etc.
- **Mock Adapters**: Testing and development adapters that simulate real provider behavior

### Intelligent Routing Engine
The routing engine evaluates quotes based on multiple factors:

- **Cost Optimization**: Find the most economical options
- **Time Optimization**: Prioritize speed and reliability
- **Quality Scoring**: Factor in worker ratings and provider reliability
- **Priority Handling**: Adjust recommendations based on urgency

## 📖 API Reference

### Core Endpoints

#### Request Movement Quotes
```http
POST /api/v1/movement/request
Authorization: Bearer YOUR_API_KEY

{
    "service_type": "delivery|rideshare|courier|freight|gig_work",
    "pickup_location": {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "address": "123 Main St, San Francisco, CA"
    },
    "dropoff_location": {
        "latitude": 37.7849,
        "longitude": -122.4094,
        "address": "456 Oak Ave, San Francisco, CA"
    },
    "priority": "low|normal|high|urgent",
    "requested_pickup_time": "2024-01-15T14:30:00Z",
    "special_requirements": {
        "passenger_count": 2,
        "package_weight_kg": 5.0,
        "fragile": true
    }
}
```

#### Accept Quote and Create Job
```http
POST /api/v1/movement/accept?quote_id=QUOTE_ID
Authorization: Bearer YOUR_API_KEY

{
    "service_type": "delivery",
    "pickup_location": {...},
    "dropoff_location": {...},
    "contact_info": {
        "name": "John Doe",
        "phone": "+15551234567"
    }
}
```

#### Track Job Status
```http
GET /api/v1/jobs/{job_id}/status
Authorization: Bearer YOUR_API_KEY
```

#### Real-time Job Tracking
```http
GET /api/v1/jobs/{job_id}/track
Authorization: Bearer YOUR_API_KEY
```

#### WebSocket Real-time Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws');

ws.onopen = () => {
    // Subscribe to job updates
    ws.send(JSON.stringify({
        type: 'subscribe_job',
        job_id: 'your_job_id'
    }));
};

ws.onmessage = (event) => {
    const update = JSON.parse(event.data);
    console.log('Job update:', update);
};
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application settings
DEBUG=true
SECRET_KEY=your-super-secret-key-change-this

# Database
DATABASE_URL=postgresql://user:password@localhost/tesseracts_world

# Redis
REDIS_URL=redis://localhost:6379

# Provider API Keys
UBER_API_KEY=your_uber_api_key
LYFT_API_KEY=your_lyft_api_key
DOORDASH_API_KEY=your_doordash_api_key

# Rate limiting
REQUESTS_PER_MINUTE=100
REQUESTS_PER_HOUR=1000
```

### Provider Configuration

Add new providers by implementing the `ProviderAdapter` interface:

```python
from src.adapters.base import ProviderAdapter

class CustomProviderAdapter(ProviderAdapter):
    async def get_quote(self, request: MovementRequest) -> Optional[Quote]:
        # Implement provider-specific quote logic
        pass
    
    async def create_job(self, quote_id: str, request: MovementRequest) -> Job:
        # Implement provider-specific job creation
        pass
    
    # ... implement other required methods
```

## 🧪 Testing

### Run Tests
```bash
pytest tests/
```

### Run Example Applications
```bash
# Rideshare aggregator demo
python examples/rideshare_aggregator.py

# Delivery orchestration demo  
python examples/delivery_orchestrator.py
```

### Manual API Testing
```bash
# Start the API
python -m src.api.main

# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test movement request
curl -X POST http://localhost:8000/api/v1/movement/request \\
  -H "Authorization: Bearer tesseracts_demo_key_12345" \\
  -H "Content-Type: application/json" \\
  -d '{
    "service_type": "delivery",
    "pickup_location": {"latitude": 37.7749, "longitude": -122.4194},
    "dropoff_location": {"latitude": 37.7849, "longitude": -122.4094},
    "priority": "normal"
  }'
```

## 🎯 Business Applications

### For Developers and Platforms
- **Rapid Integration**: Single API integration vs. dozens of separate provider APIs
- **Global Coverage**: Instant access to worldwide network of movement providers
- **Cost Optimization**: Intelligent routing finds the best price/performance balance
- **Reduced Complexity**: No need to manage multiple provider relationships

### For Businesses
- **Hotel Chains**: Offer guests unified rideshare access across all properties
- **E-commerce**: Dynamic delivery routing for optimal cost and speed
- **Event Organizers**: Coordinate transportation for thousands of attendees
- **Marketplaces**: Enable sellers to offer multiple shipping options seamlessly

### For Gig Workers
- **Unified Job Feed**: Access jobs from multiple platforms in one interface
- **Optimized Routing**: AI-powered job recommendations based on location and preferences
- **Flexible Work**: Choose from rideshare, delivery, courier, and other gig opportunities

## 🔄 Integration Examples

### React Native Mobile App
```javascript
import TesseractsSDK from '@tesseracts/react-native-sdk';

const tesseracts = new TesseractsSDK('your_api_key');

// Request ride quotes
const quotes = await tesseracts.requestMovement({
    serviceType: 'rideshare',
    pickupLocation: {latitude: 37.7749, longitude: -122.4194},
    dropoffLocation: {latitude: 37.7849, longitude: -122.4094}
});

// Book the recommended option
const job = await tesseracts.acceptQuote(quotes.recommendedQuoteId);

// Track in real-time
tesseracts.trackJob(job.id, (update) => {
    console.log('Location update:', update.location);
});
```

### Backend Integration (Node.js)
```javascript
const { TesseractsClient } = require('@tesseracts/node-sdk');

const client = new TesseractsClient('your_api_key');

// Batch process delivery orders
const orders = await getOrdersFromDatabase();
const deliveries = orders.map(order => ({
    serviceType: 'delivery',
    pickupLocation: order.warehouse,
    dropoffLocation: order.customer,
    packageDetails: order.package
}));

const results = await client.batchScheduleDeliveries(deliveries);
```

## 📊 Analytics and Monitoring

### Real-time Analytics
```http
GET /api/v1/analytics
Authorization: Bearer YOUR_API_KEY
```

Returns comprehensive metrics:
- Total jobs processed
- Success/failure rates by provider
- Average costs and delivery times
- Geographic distribution
- Provider health status

### Custom Webhooks
Configure webhooks to receive job status updates:

```python
# Configure webhook endpoint
await client.configure_webhook({
    "url": "https://your-app.com/tesseracts/webhook",
    "events": ["job.created", "job.completed", "job.cancelled"],
    "secret": "your_webhook_secret"
})
```

## 🏢 Enterprise Features

### Advanced Routing
- **Machine Learning Optimization**: Continuously improving route selection based on historical performance
- **Geographic Partitioning**: Intelligent provider selection based on coverage areas
- **Load Balancing**: Distribute requests across providers to prevent bottlenecks
- **Failover Handling**: Automatic fallback to alternative providers

### Security and Compliance
- **SOC 2 Compliance**: Enterprise-grade security standards
- **Data Encryption**: End-to-end encryption for sensitive customer data
- **Audit Logging**: Comprehensive logging for compliance and debugging
- **GDPR Support**: Privacy-compliant data handling and deletion

### Scale and Performance
- **Horizontal Scaling**: Auto-scaling infrastructure for high-volume operations
- **Global CDN**: Low-latency API access worldwide
- **99.9% Uptime SLA**: Enterprise reliability guarantees
- **Dedicated Support**: 24/7 technical support for enterprise customers

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linting
black src/ tests/
flake8 src/ tests/
mypy src/

# Start development server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## 📞 Support

### Documentation
- **API Documentation**: [https://docs.tesseractsworld.com](https://docs.tesseractsworld.com)
- **Integration Guides**: [https://guides.tesseractsworld.com](https://guides.tesseractsworld.com)
- **SDK Reference**: [https://sdk.tesseractsworld.com](https://sdk.tesseractsworld.com)

### Community
- **Discord**: [Join our developer community](https://discord.gg/tesseracts)
- **GitHub Issues**: [Report bugs and request features](https://github.com/tesseracts-world/api/issues)
- **Stack Overflow**: Tag questions with `tesseracts-world`

### Enterprise Support
- **Email**: enterprise@tesseractsworld.com
- **Slack**: Available for enterprise customers
- **Phone**: 1-800-TESSERACT

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation and settings
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [Redis](https://redis.io/) - In-memory data structure store
- [Celery](https://celeryproject.org/) - Distributed task queue

---

**Tesseracts World** - Route anything, anywhere. 🌍✨
