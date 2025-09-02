from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

from ..models.commerce import Seller, Product, Order, OrderItem, Payment, PaymentMethod, EscrowStatus, OrderStatus, Address
from ..models.core import MovementRequest, ServiceType, Location
from ..database.repositories import ProductRepository, SellerRepository, OrderRepository
from ..database.models import ProductDB, SellerDB, OrderDB
from ..database import db_manager
from .gateway import TesseractsGateway

class CatalogService:
    """Database-backed catalog service for managing sellers and products."""
    
    async def register_seller(self, seller: Seller) -> Seller:
        async with db_manager.get_session() as session:
            seller_repo = SellerRepository(session)
            await seller_repo.create(seller)
            return seller

    async def get_seller(self, seller_id: str) -> Optional[Seller]:
        async with db_manager.get_session() as session:
            seller_repo = SellerRepository(session)
            seller_db = await seller_repo.get_by_id(seller_id)
            if seller_db:
                return self._convert_seller_from_db(seller_db)
            return None

    async def publish_product(self, product: Product) -> Product:
        async with db_manager.get_session() as session:
            seller_repo = SellerRepository(session)
            product_repo = ProductRepository(session)
            
            # Validate seller exists
            seller_exists = await seller_repo.get_by_id(product.seller_id)
            if not seller_exists:
                raise ValueError("Seller not found")
            
            await product_repo.create(product, product.seller_id)
            return product

    async def get_product(self, product_id: str) -> Optional[Product]:
        async with db_manager.get_session() as session:
            product_repo = ProductRepository(session)
            product_db = await product_repo.get_by_id(product_id)
            if product_db:
                return self._convert_product_from_db(product_db)
            return None

    async def list_products(self, seller_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Product]:
        async with db_manager.get_session() as session:
            product_repo = ProductRepository(session)
            if seller_id:
                products_db = await product_repo.get_by_seller(seller_id, skip, limit)
            else:
                products_db = await product_repo.search(skip=skip, limit=limit)
            
            return [self._convert_product_from_db(p) for p in products_db]

    async def search(self, query: str = "", categories: Optional[List[str]] = None, 
                    min_price: Optional[float] = None, max_price: Optional[float] = None,
                    skip: int = 0, limit: int = 100) -> List[Product]:
        async with db_manager.get_session() as session:
            product_repo = ProductRepository(session)
            products_db = await product_repo.search(
                query=query if query else None,
                categories=categories,
                min_price=min_price,
                max_price=max_price,
                skip=skip,
                limit=limit
            )
            
            return [self._convert_product_from_db(p) for p in products_db]
    
    def _convert_seller_from_db(self, seller_db: SellerDB) -> Seller:
        """Convert database seller to domain model."""
        from ..models.commerce import DecentralizedIdentity
        return Seller(
            id=seller_db.id,
            name=seller_db.name,
            did=DecentralizedIdentity(
                method=seller_db.did_method,
                identifier=seller_db.did_identifier
            ),
            reputation_score=seller_db.reputation_score,
            metadata=seller_db.metadata or {}
        )
    
    def _convert_product_from_db(self, product_db: ProductDB) -> Product:
        """Convert database product to domain model."""
        return Product(
            id=product_db.id,
            seller_id=product_db.seller_id,
            title=product_db.title,
            description=product_db.description,
            sku=product_db.sku,
            price=product_db.price,
            currency=product_db.currency,
            weight_kg=product_db.weight_kg,
            dimensions_cm=product_db.dimensions_cm or {},
            categories=product_db.categories or [],
            images=product_db.images or [],
            inventory=product_db.inventory,
            fulfillment_origin=product_db.fulfillment_origin or {},
            attributes=product_db.attributes or {}
        )

class PaymentService:
    def initiate_crypto_escrow(self, amount: float, currency: str) -> Payment:
        # Mock: pretend we created an escrow on-chain and return a reference
        ref = f"0x{uuid4().hex[:16]}"
        return Payment(method=PaymentMethod.CRYPTO, amount=amount, currency=currency, escrow_status=EscrowStatus.INITIATED, reference=ref)

    def fund_escrow(self, payment: Payment) -> Payment:
        payment.escrow_status = EscrowStatus.FUNDED
        return payment

    def release_escrow(self, payment: Payment) -> Payment:
        payment.escrow_status = EscrowStatus.RELEASED
        return payment

class OrderService:
    """Database-backed order service for managing orders and delivery."""
    
    def __init__(self, catalog: CatalogService, gateway: TesseractsGateway):
        self.catalog = catalog
        self.gateway = gateway

    async def create_order(self, seller_id: str, items: List[OrderItem], dropoff: Address, buyer_did_identifier: str) -> Order:
        async with db_manager.get_session() as session:
            seller_repo = SellerRepository(session)
            product_repo = ProductRepository(session)
            order_repo = OrderRepository(session)
            
            # Validate seller exists
            seller_db = await seller_repo.get_by_id(seller_id)
            if not seller_db:
                raise ValueError("Seller not found")
            
            subtotal = 0.0
            pickup_origin: Optional[Address] = None
            validated_items = []
            
            # Validate products and calculate totals
            for item in items:
                product_db = await product_repo.get_by_id(item.product_id)
                if not product_db or product_db.seller_id != seller_id:
                    raise ValueError(f"Invalid product {item.product_id}")
                if product_db.inventory < item.quantity:
                    raise ValueError(f"Insufficient inventory for {product_db.title}")
                
                subtotal += item.unit_price * item.quantity
                validated_items.append(item)
                
                # Set pickup location from first product with origin
                if not pickup_origin and product_db.fulfillment_origin:
                    pickup_origin = Address(
                        name=seller_db.name,
                        latitude=product_db.fulfillment_origin.get("latitude"),
                        longitude=product_db.fulfillment_origin.get("longitude"),
                        address=product_db.fulfillment_origin.get("address"),
                    )
            
            if not pickup_origin:
                raise ValueError("No fulfillment origin found for seller")
            
            # Create order domain model
            from ..models.commerce import DecentralizedIdentity
            order = Order(
                seller_id=seller_id,
                buyer=DecentralizedIdentity(method="did:key", identifier=buyer_did_identifier),
                items=validated_items,
                subtotal=subtotal,
                total=subtotal,  # Delivery fee added later
                pickup=pickup_origin,
                dropoff=dropoff,
            )
            
            # Save to database
            await order_repo.create(order)
            return order

    async def get_order(self, order_id: str) -> Optional[Order]:
        async with db_manager.get_session() as session:
            order_repo = OrderRepository(session)
            order_db = await order_repo.get_by_id(order_id)
            if order_db:
                return self._convert_order_from_db(order_db)
            return None

    async def request_delivery_quotes(self, order_id: str):
        async with db_manager.get_session() as session:
            order_repo = OrderRepository(session)
            order_db = await order_repo.get_by_id(order_id)
            
            if not order_db:
                raise ValueError("Order not found")
            
            req = MovementRequest(
                service_type=ServiceType.DELIVERY,
                pickup_location=Location(
                    latitude=order_db.pickup_latitude, 
                    longitude=order_db.pickup_longitude
                ),
                dropoff_location=Location(
                    latitude=order_db.dropoff_latitude, 
                    longitude=order_db.dropoff_longitude
                ),
            )
            
            response = await self.gateway.request_movement(req)
            
            # Update order with movement request ID
            await order_repo.set_movement_info(order_id, movement_request_id=response.request_id)
            return response

    async def accept_delivery_and_book(self, order_id: str, quote_id: str):
        async with db_manager.get_session() as session:
            order_repo = OrderRepository(session)
            order_db = await order_repo.get_by_id(order_id)
            
            if not order_db:
                raise ValueError("Order not found")
            
            # Recreate movement request context
            req = MovementRequest(
                service_type=ServiceType.DELIVERY,
                pickup_location=Location(
                    latitude=order_db.pickup_latitude, 
                    longitude=order_db.pickup_longitude
                ),
                dropoff_location=Location(
                    latitude=order_db.dropoff_latitude, 
                    longitude=order_db.dropoff_longitude
                ),
            )
            
            job = await self.gateway.accept_quote(quote_id, req)
            
            # Update order with job ID and status
            await order_repo.set_movement_info(
                order_id, 
                movement_job_id=job.id
            )
            await order_repo.update_status(order_id, "fulfilling")
            
            return job

    async def reduce_inventory(self, order_id: str):
        """Reduce inventory for order items."""
        async with db_manager.get_session() as session:
            order_repo = OrderRepository(session)
            product_repo = ProductRepository(session)
            
            order_db = await order_repo.get_by_id(order_id)
            if not order_db:
                return
            
            for item_db in order_db.items:
                await product_repo.update_inventory(item_db.product_id, -item_db.quantity)
    
    def _convert_order_from_db(self, order_db: OrderDB) -> Order:
        """Convert database order to domain model."""
        from ..models.commerce import DecentralizedIdentity
        
        # Convert items
        items = []
        for item_db in order_db.items:
            items.append(OrderItem(
                product_id=item_db.product_id,
                title=item_db.title,
                quantity=item_db.quantity,
                unit_price=item_db.unit_price,
                currency=item_db.currency,
                weight_kg=item_db.weight_kg
            ))
        
        return Order(
            id=order_db.id,
            seller_id=order_db.seller_id,
            buyer=DecentralizedIdentity(
                method=order_db.buyer_did_method,
                identifier=order_db.buyer_did_identifier
            ),
            items=items,
            subtotal=order_db.subtotal,
            delivery_fee=order_db.delivery_fee,
            total=order_db.total,
            status=OrderStatus(order_db.status),
            pickup=Address(
                name=order_db.pickup_name,
                phone=order_db.pickup_phone,
                address=order_db.pickup_address,
                latitude=order_db.pickup_latitude,
                longitude=order_db.pickup_longitude
            ),
            dropoff=Address(
                name=order_db.dropoff_name,
                phone=order_db.dropoff_phone,
                address=order_db.dropoff_address,
                latitude=order_db.dropoff_latitude,
                longitude=order_db.dropoff_longitude
            ),
            movement_request_id=order_db.movement_request_id,
            movement_job_id=order_db.movement_job_id,
            created_at=order_db.created_at,
            updated_at=order_db.updated_at
        )

# Singletons (in-memory for now)
_catalog_service: Optional[CatalogService] = None
_payment_service: Optional[PaymentService] = None
_order_service: Optional[OrderService] = None


def get_catalog_service() -> CatalogService:
    global _catalog_service
    if _catalog_service is None:
        _catalog_service = CatalogService()
    return _catalog_service

def get_payment_service() -> PaymentService:
    global _payment_service
    if _payment_service is None:
        _payment_service = PaymentService()
    return _payment_service

def get_order_service(gateway: TesseractsGateway) -> OrderService:
    global _order_service
    if _order_service is None:
        _order_service = OrderService(get_catalog_service(), gateway)
    return _order_service

