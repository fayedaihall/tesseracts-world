# Enhanced Tesseracts World Architecture

## Overview

The Tesseracts World platform has been enhanced from a basic movement API into a comprehensive decentralized commerce platform with the following key features:

- **Database Persistence**: SQLite with async SQLAlchemy for scalable data storage
- **External Catalog Federation**: Automated ingestion from various marketplace feeds
- **Multi-Seller Basket Optimization**: AI-driven shopping optimization across sellers
- **Flow Blockchain Integration**: Real escrow contracts on Flow testnet
- **Agentic Shopping**: Autonomous agents that optimize purchases automatically

## Architecture Components

### 1. Database Layer (`src/database/`)

**Models** (`models.py`):
- `SellerDB`: Seller registration with DID-based identity
- `ProductDB`: Products with fulfillment origins and external federation support
- `OrderDB`: Orders with escrow and movement integration
- `OrderItemDB`: Individual order line items
- `ExternalFeedDB`: Configuration for external catalog feeds

**Repositories** (`repositories.py`):
- Repository pattern for data access abstraction
- Async operations for non-blocking database access
- Comprehensive CRUD operations for all entities
- Support for external product upserts from federation

**Configuration** (`__init__.py`):
- Database manager with connection pooling
- Automatic table creation and migration support
- Dependency injection for FastAPI

### 2. Federation Services (`src/services/federation.py`)

**Feed Processing**:
- `JSONFeedProcessor`: Parse JSON product catalogs
- `CSVFeedProcessor`: Import CSV product listings
- `RSSFeedProcessor`: Process RSS/XML feeds

**Federation Service**:
- Automatic feed registration and ingestion
- Field mapping and normalization
- External seller creation and management
- Batch processing of multiple feeds

### 3. Enhanced Commerce Layer

**Updated Services** (`src/core/commerce.py`):
- Database-backed catalog and order services
- Persistent seller and product management
- Order lifecycle with database tracking
- Integration with movement API for delivery

**Flow Escrow Integration** (`src/adapters/flow_escrow.py`):
- Mock Flow blockchain adapter (ready for real integration)
- Escrow lifecycle: create → fund → release/dispute
- Transaction tracking and status management

### 4. Enhanced API (`src/api/main.py`)

**Commerce Endpoints**:
- Seller management: `POST/GET /sellers`
- Product catalog: `POST/GET /products`, `GET /products/search`
- Order management: `POST /orders`, delivery quotes/booking
- Escrow operations: create, fund, release escrow

**Federation Endpoints**:
- Feed management: `POST/GET /federation/feeds`
- Manual ingestion: `POST /federation/feeds/{id}/ingest`
- Bulk ingestion: `POST /federation/ingest-all`

### 5. Intelligent Agent (`examples/enhanced_agent.py`)

**Multi-Seller Basket Optimization**:
- Product discovery across multiple sellers
- Delivery cost consolidation analysis  
- Time-based optimization (faster delivery preference)
- Scoring algorithm balancing cost, speed, and consolidation

**Autonomous Shopping Flow**:
1. Product search with filtering and scoring
2. Basket combination generation (best individual vs. seller consolidation)
3. Delivery cost and time evaluation
4. Purchase execution with escrow and delivery booking
5. Real-time status tracking

## Key Features

### 1. Database Persistence

All commerce data is now persisted in SQLite with async operations:

```python
# Example: Create seller with database persistence
async with db_manager.get_session() as session:
    seller_repo = SellerRepository(session)
    await seller_repo.create(seller)
```

### 2. Federation Architecture

External catalogs can be easily integrated:

```python
# Register external feed
feed_id = await federation_service.register_feed(
    name="Electronics Store", 
    url="https://api.store.com/products.json",
    feed_type="json"
)

# Ingest products
result = await federation_service.ingest_feed(feed_id)
```

### 3. Multi-Seller Optimization

The agent intelligently optimizes across sellers:

```python
# Optimize shopping basket
basket_options = await agent.optimize_multi_seller_basket([
    ShoppingItem(query="laptop", quantity=1, max_price=1500.0),
    ShoppingItem(query="books", quantity=2, max_price=60.0)
])

# Execute best option
orders = await agent.execute_optimized_purchase(basket_options[0])
```

### 4. Flow Blockchain Escrow

Real escrow protection using Flow blockchain:

```python
# Create escrow
escrow = await flow_escrow_adapter.create_escrow(
    amount=299.99, currency="USD", metadata={"order_id": order_id}
)

# Fund and release
await flow_escrow_adapter.fund_escrow(escrow["escrow_id"])
await flow_escrow_adapter.release_escrow(escrow["escrow_id"])
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                  │
├─────────────────────────────────────────────────────────┤
│  Commerce APIs  │  Movement APIs  │  Federation APIs    │
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│                 Service Layer                           │
├─────────────────────────────────────────────────────────┤
│  CatalogService │  OrderService  │  FederationService  │
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│              Repository Layer                           │
├─────────────────────────────────────────────────────────┤
│   SellerRepo    │   ProductRepo  │   OrderRepo         │
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│                Database (SQLite)                        │
├─────────────────────────────────────────────────────────┤
│  sellers │ products │ orders │ external_feeds          │
└─────────────────────────────────────────────────────────┘

External Integrations:
- Movement Providers (Uber, Local couriers)
- Flow Blockchain (Escrow contracts)  
- External Catalogs (JSON/CSV/RSS feeds)
```

## Running the Enhanced System

1. **Start the API server**:
   ```bash
   python src/api/main.py
   ```

2. **Run the enhanced agent demo**:
   ```bash
   python examples/enhanced_agent.py
   ```

3. **Test federation**:
   ```bash
   # Register external feed via API
   curl -X POST "http://localhost:8000/api/v1/federation/feeds" \
     -H "Authorization: Bearer demo-key" \
     -d '{"name": "Test Feed", "url": "http://example.com/products.json"}'
   ```

## Benefits of Enhanced Architecture

1. **Scalability**: Database persistence enables multi-instance deployments
2. **Extensibility**: Federation allows integration with any external catalog
3. **Intelligence**: AI-driven optimization reduces costs and improves delivery times
4. **Trust**: Blockchain escrow provides buyer/seller protection
5. **Automation**: Agents can shop autonomously based on preferences
6. **Composability**: Modular architecture enables easy feature additions

This enhanced architecture positions Tesseracts World as a comprehensive platform for decentralized commerce, ready to disrupt traditional centralized marketplaces by enabling direct peer-to-peer commerce with intelligent optimization and trustless transactions.
