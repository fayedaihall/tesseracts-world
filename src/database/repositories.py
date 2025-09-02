from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

from .models import SellerDB, ProductDB, OrderDB, OrderItemDB, ExternalFeedDB
from ..models import Seller, Product, Order, OrderItem


class BaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


class SellerRepository(BaseRepository):
    async def create(self, seller: Seller) -> SellerDB:
        """Create a new seller."""
        seller_db = SellerDB(
            id=seller.id,
            name=seller.name,
            did_method=seller.did.method,
            did_identifier=seller.did.identifier,
            website=seller.metadata.get("website"),
            contact_email=seller.metadata.get("contact_email"),
            reputation_score=seller.reputation_score,
            metadata=seller.metadata
        )
        self.session.add(seller_db)
        await self.session.commit()
        await self.session.refresh(seller_db)
        return seller_db
    
    async def get_by_id(self, seller_id: str) -> Optional[SellerDB]:
        """Get seller by ID."""
        stmt = select(SellerDB).where(SellerDB.id == seller_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_did(self, did_identifier: str) -> Optional[SellerDB]:
        """Get seller by DID identifier."""
        stmt = select(SellerDB).where(SellerDB.did_identifier == did_identifier)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[SellerDB]:
        """List all sellers."""
        stmt = select(SellerDB).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update(self, seller_id: str, updates: Dict[str, Any]) -> Optional[SellerDB]:
        """Update seller."""
        stmt = update(SellerDB).where(SellerDB.id == seller_id).values(**updates)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(seller_id)
    
    async def delete(self, seller_id: str) -> bool:
        """Delete seller."""
        stmt = delete(SellerDB).where(SellerDB.id == seller_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0


class ProductRepository(BaseRepository):
    async def create(self, product: Product, seller_id: str) -> ProductDB:
        """Create a new product."""
        product_db = ProductDB(
            id=product.id,
            seller_id=seller_id,
            title=product.title,
            description=product.description,
            sku=product.sku,
            price=product.price,
            currency=product.currency,
            weight_kg=product.weight_kg,
            dimensions_cm=product.dimensions_cm,
            categories=product.categories,
            images=product.images,
            inventory=product.inventory,
            fulfillment_origin=product.fulfillment_origin,
            attributes=product.attributes
        )
        self.session.add(product_db)
        await self.session.commit()
        await self.session.refresh(product_db)
        return product_db
    
    async def get_by_id(self, product_id: str) -> Optional[ProductDB]:
        """Get product by ID with seller info."""
        stmt = select(ProductDB).options(selectinload(ProductDB.seller)).where(ProductDB.id == product_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def search(self, query: str = None, categories: List[str] = None, 
                    seller_id: str = None, min_price: float = None, max_price: float = None,
                    skip: int = 0, limit: int = 100) -> List[ProductDB]:
        """Search products with filters."""
        stmt = select(ProductDB).options(selectinload(ProductDB.seller))
        
        filters = []
        if query:
            filters.append(or_(
                ProductDB.title.ilike(f"%{query}%"),
                ProductDB.description.ilike(f"%{query}%")
            ))
        if categories:
            # JSON containment check - simplified for SQLite
            for category in categories:
                filters.append(ProductDB.categories.contains([category]))
        if seller_id:
            filters.append(ProductDB.seller_id == seller_id)
        if min_price is not None:
            filters.append(ProductDB.price >= min_price)
        if max_price is not None:
            filters.append(ProductDB.price <= max_price)
        
        if filters:
            stmt = stmt.where(and_(*filters))
        
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_seller(self, seller_id: str, skip: int = 0, limit: int = 100) -> List[ProductDB]:
        """Get products by seller."""
        stmt = select(ProductDB).where(ProductDB.seller_id == seller_id).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_inventory(self, product_id: str, quantity_change: int) -> Optional[ProductDB]:
        """Update product inventory."""
        stmt = update(ProductDB).where(ProductDB.id == product_id).values(
            inventory=ProductDB.inventory + quantity_change,
            updated_at=datetime.utcnow()
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(product_id)
    
    async def upsert_external(self, product_data: Dict[str, Any], external_source: str) -> ProductDB:
        """Upsert product from external source."""
        # Check if product already exists from this source
        stmt = select(ProductDB).where(
            and_(
                ProductDB.external_id == product_data["external_id"],
                ProductDB.external_source == external_source
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing product
            update_data = {**product_data, "updated_at": datetime.utcnow()}
            stmt = update(ProductDB).where(ProductDB.id == existing.id).values(**update_data)
            await self.session.execute(stmt)
            await self.session.commit()
            return await self.get_by_id(existing.id)
        else:
            # Create new product
            product_db = ProductDB(
                id=str(uuid.uuid4()),
                external_source=external_source,
                **product_data
            )
            self.session.add(product_db)
            await self.session.commit()
            await self.session.refresh(product_db)
            return product_db


class OrderRepository(BaseRepository):
    async def create(self, order: Order) -> OrderDB:
        """Create a new order with items."""
        # Create order record
        order_db = OrderDB(
            id=order.id,
            buyer_did_method=order.buyer.method,
            buyer_did_identifier=order.buyer.identifier,
            seller_id=order.seller_id,
            subtotal=order.subtotal,
            currency=order.currency,
            delivery_fee=order.delivery_fee,
            total=order.total,
            status=order.status,
            pickup_name=order.pickup.name,
            pickup_phone=order.pickup.phone,
            pickup_address=order.pickup.address,
            pickup_latitude=order.pickup.latitude,
            pickup_longitude=order.pickup.longitude,
            dropoff_name=order.dropoff.name,
            dropoff_phone=order.dropoff.phone,
            dropoff_address=order.dropoff.address,
            dropoff_latitude=order.dropoff.latitude,
            dropoff_longitude=order.dropoff.longitude
        )
        self.session.add(order_db)
        
        # Create order items
        for item in order.items:
            item_db = OrderItemDB(
                order_id=order.id,
                product_id=item.product_id,
                title=item.title,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency=item.currency,
                weight_kg=item.weight_kg
            )
            self.session.add(item_db)
        
        await self.session.commit()
        await self.session.refresh(order_db)
        return order_db
    
    async def get_by_id(self, order_id: str) -> Optional[OrderDB]:
        """Get order by ID with all relationships."""
        stmt = select(OrderDB).options(
            selectinload(OrderDB.items),
            selectinload(OrderDB.seller)
        ).where(OrderDB.id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_buyer(self, buyer_did: str, skip: int = 0, limit: int = 100) -> List[OrderDB]:
        """Get orders by buyer DID."""
        stmt = select(OrderDB).options(
            selectinload(OrderDB.items),
            selectinload(OrderDB.seller)
        ).where(OrderDB.buyer_did_identifier == buyer_did).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_seller(self, seller_id: str, skip: int = 0, limit: int = 100) -> List[OrderDB]:
        """Get orders by seller."""
        stmt = select(OrderDB).options(
            selectinload(OrderDB.items)
        ).where(OrderDB.seller_id == seller_id).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_status(self, order_id: str, status: str, **kwargs) -> Optional[OrderDB]:
        """Update order status and optional additional fields."""
        update_data = {"status": status, "updated_at": datetime.utcnow(), **kwargs}
        stmt = update(OrderDB).where(OrderDB.id == order_id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(order_id)
    
    async def set_payment_info(self, order_id: str, payment_id: str, payment_method: str, 
                              payment_amount: float) -> Optional[OrderDB]:
        """Set payment information."""
        return await self.update_status(
            order_id, "payment_pending",
            payment_id=payment_id,
            payment_method=payment_method,
            payment_amount=payment_amount
        )
    
    async def set_escrow_info(self, order_id: str, escrow_status: str, 
                             escrow_reference: str = None, flow_escrow_id: str = None) -> Optional[OrderDB]:
        """Set escrow information."""
        update_data = {"escrow_status": escrow_status}
        if escrow_reference:
            update_data["escrow_reference"] = escrow_reference
        if flow_escrow_id:
            update_data["flow_escrow_id"] = flow_escrow_id
        
        return await self.update_status(order_id, "escrow_funded", **update_data)
    
    async def set_movement_info(self, order_id: str, movement_request_id: str = None, 
                               movement_job_id: str = None) -> Optional[OrderDB]:
        """Set movement/delivery information."""
        update_data = {}
        if movement_request_id:
            update_data["movement_request_id"] = movement_request_id
        if movement_job_id:
            update_data["movement_job_id"] = movement_job_id
        
        return await self.update_status(order_id, "in_delivery", **update_data)


class ExternalFeedRepository(BaseRepository):
    async def create(self, feed_id: str, name: str, url: str, feed_type: str = "json", 
                    config: Dict[str, Any] = None) -> ExternalFeedDB:
        """Create external feed configuration."""
        feed_db = ExternalFeedDB(
            id=feed_id,
            name=name,
            url=url,
            feed_type=feed_type,
            config=config or {}
        )
        self.session.add(feed_db)
        await self.session.commit()
        await self.session.refresh(feed_db)
        return feed_db
    
    async def get_by_id(self, feed_id: str) -> Optional[ExternalFeedDB]:
        """Get feed by ID."""
        stmt = select(ExternalFeedDB).where(ExternalFeedDB.id == feed_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_active(self) -> List[ExternalFeedDB]:
        """List active feeds."""
        stmt = select(ExternalFeedDB).where(ExternalFeedDB.status == "active")
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_fetch_status(self, feed_id: str, success: bool) -> Optional[ExternalFeedDB]:
        """Update feed fetch status."""
        now = datetime.utcnow()
        update_data = {"last_fetched": now}
        if success:
            update_data["last_success"] = now
        
        stmt = update(ExternalFeedDB).where(ExternalFeedDB.id == feed_id).values(**update_data)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(feed_id)
