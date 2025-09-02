import asyncio
import aiohttp
import uuid
import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from xml.etree import ElementTree as ET
import json
import csv
from io import StringIO

from ..database.repositories import ProductRepository, SellerRepository, ExternalFeedRepository
from ..database import db_manager
from ..models import Product, Seller, DecentralizedIdentity


logger = logging.getLogger(__name__)


class FeedProcessor:
    """Base class for processing different feed types."""
    
    def __init__(self, feed_config: Dict[str, Any]):
        self.config = feed_config
    
    async def process(self, content: str) -> List[Dict[str, Any]]:
        """Process feed content and return list of product data."""
        raise NotImplementedError


class JSONFeedProcessor(FeedProcessor):
    """Process JSON product feeds."""
    
    async def process(self, content: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(content)
            
            # Handle different JSON structures
            if isinstance(data, list):
                products = data
            elif isinstance(data, dict):
                # Look for products array in common keys
                products = data.get('products', data.get('items', data.get('data', [])))
            else:
                products = []
            
            processed = []
            for item in products:
                product_data = await self._normalize_product(item)
                if product_data:
                    processed.append(product_data)
            
            return processed
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in feed: {e}")
            return []
    
    async def _normalize_product(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize product data to standard format."""
        try:
            # Map common field variations
            field_mapping = self.config.get('field_mapping', {})
            
            # Default field mappings
            default_mapping = {
                'id': ['id', 'product_id', 'sku', 'external_id'],
                'title': ['title', 'name', 'product_name'],
                'description': ['description', 'desc', 'summary'],
                'price': ['price', 'cost', 'amount'],
                'sku': ['sku', 'code', 'product_code'],
                'weight_kg': ['weight', 'weight_kg', 'weight_grams'],
                'categories': ['categories', 'category', 'tags'],
                'images': ['images', 'image_urls', 'photos'],
                'inventory': ['inventory', 'stock', 'quantity']
            }
            
            normalized = {}
            for standard_field, possible_fields in default_mapping.items():
                # Check custom mapping first
                if standard_field in field_mapping:
                    field_name = field_mapping[standard_field]
                    if field_name in item:
                        normalized[standard_field] = item[field_name]
                else:
                    # Try possible field names
                    for field_name in possible_fields:
                        if field_name in item:
                            normalized[standard_field] = item[field_name]
                            break
            
            # Required fields check
            if not normalized.get('id') or not normalized.get('title'):
                logger.warning(f"Missing required fields in product: {item}")
                return None
            
            # Type conversions and defaults
            normalized['external_id'] = str(normalized.get('id', ''))
            normalized['price'] = float(normalized.get('price', 0))
            normalized['weight_kg'] = float(normalized.get('weight_kg', 0)) / 1000 if 'weight_grams' in item else float(normalized.get('weight_kg', 0))
            normalized['inventory'] = int(normalized.get('inventory', 0))
            
            # Ensure categories and images are lists
            if 'categories' in normalized and not isinstance(normalized['categories'], list):
                normalized['categories'] = [normalized['categories']]
            if 'images' in normalized and not isinstance(normalized['images'], list):
                normalized['images'] = [normalized['images']] if normalized['images'] else []
            
            # Set defaults
            normalized.setdefault('categories', [])
            normalized.setdefault('images', [])
            normalized.setdefault('currency', 'USD')
            normalized.setdefault('attributes', {})
            normalized.setdefault('fulfillment_origin', {})
            
            return normalized
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Error normalizing product {item}: {e}")
            return None


class CSVFeedProcessor(FeedProcessor):
    """Process CSV product feeds."""
    
    async def process(self, content: str) -> List[Dict[str, Any]]:
        try:
            csv_reader = csv.DictReader(StringIO(content))
            processed = []
            
            for row in csv_reader:
                product_data = await self._normalize_product(row)
                if product_data:
                    processed.append(product_data)
            
            return processed
        except Exception as e:
            logger.error(f"Error processing CSV feed: {e}")
            return []
    
    async def _normalize_product(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Normalize CSV row to product data."""
        try:
            # Use similar logic as JSON processor
            json_processor = JSONFeedProcessor(self.config)
            return await json_processor._normalize_product(row)
        except Exception as e:
            logger.warning(f"Error normalizing CSV row {row}: {e}")
            return None


class RSSFeedProcessor(FeedProcessor):
    """Process RSS/XML product feeds."""
    
    async def process(self, content: str) -> List[Dict[str, Any]]:
        try:
            root = ET.fromstring(content)
            processed = []
            
            # Find items in RSS/XML
            items = root.findall('.//item') or root.findall('.//product')
            
            for item in items:
                product_data = await self._normalize_product(item)
                if product_data:
                    processed.append(product_data)
            
            return processed
        except ET.ParseError as e:
            logger.error(f"Invalid XML in feed: {e}")
            return []
    
    async def _normalize_product(self, item: ET.Element) -> Optional[Dict[str, Any]]:
        """Normalize XML element to product data."""
        try:
            # Convert XML to dict
            product_dict = {}
            for child in item:
                tag = child.tag.lower()
                text = child.text or ''
                
                # Handle nested elements
                if len(child) > 0:
                    product_dict[tag] = [subchild.text for subchild in child if subchild.text]
                else:
                    product_dict[tag] = text
            
            # Use JSON processor for normalization
            json_processor = JSONFeedProcessor(self.config)
            return await json_processor._normalize_product(product_dict)
            
        except Exception as e:
            logger.warning(f"Error normalizing XML product: {e}")
            return None


class FederationService:
    """Service for managing external catalog federation."""
    
    def __init__(self):
        self.processors = {
            'json': JSONFeedProcessor,
            'csv': CSVFeedProcessor,
            'rss': RSSFeedProcessor,
            'xml': RSSFeedProcessor
        }
    
    async def ingest_feed(self, feed_id: str, seller_id: str = None) -> Dict[str, Any]:
        """Ingest products from an external feed."""
        async with db_manager.get_session() as session:
            feed_repo = ExternalFeedRepository(session)
            product_repo = ProductRepository(session)
            seller_repo = SellerRepository(session)
            
            # Get feed configuration
            feed = await feed_repo.get_by_id(feed_id)
            if not feed:
                raise ValueError(f"Feed {feed_id} not found")
            
            logger.info(f"Starting ingestion for feed {feed.name}")
            
            try:
                # Fetch feed content
                content = await self._fetch_feed_content(feed.url)
                
                # Process content based on feed type
                processor_class = self.processors.get(feed.feed_type, JSONFeedProcessor)
                processor = processor_class(feed.config)
                products_data = await processor.process(content)
                
                # Create/find seller for external products
                if not seller_id:
                    seller_id = await self._ensure_external_seller(
                        feed.name, session, seller_repo
                    )
                
                # Upsert products
                ingested_count = 0
                error_count = 0
                
                for product_data in products_data:
                    try:
                        product_data['seller_id'] = seller_id
                        await product_repo.upsert_external(product_data, feed.id)
                        ingested_count += 1
                    except Exception as e:
                        logger.error(f"Error upserting product {product_data.get('external_id')}: {e}")
                        error_count += 1
                
                # Update feed status
                await feed_repo.update_fetch_status(feed_id, success=True)
                
                result = {
                    "feed_id": feed_id,
                    "feed_name": feed.name,
                    "products_processed": len(products_data),
                    "products_ingested": ingested_count,
                    "errors": error_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Completed ingestion for feed {feed.name}: {result}")
                return result
                
            except Exception as e:
                await feed_repo.update_fetch_status(feed_id, success=False)
                logger.error(f"Feed ingestion failed for {feed.name}: {e}")
                raise
    
    async def _fetch_feed_content(self, url: str) -> str:
        """Fetch content from feed URL."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status} error fetching feed")
                return await response.text()
    
    async def _ensure_external_seller(self, feed_name: str, session, seller_repo: SellerRepository) -> str:
        """Create or find external seller for feed products."""
        external_seller_id = f"external_{feed_name.lower().replace(' ', '_')}"
        
        seller = await seller_repo.get_by_id(external_seller_id)
        if not seller:
            # Create external seller
            seller_model = Seller(
                id=external_seller_id,
                name=f"{feed_name} Marketplace",
                did=DecentralizedIdentity(method="did:web", identifier=f"external.{external_seller_id}"),
                reputation_score=0.0,
                metadata={
                    "source": "external_feed",
                    "feed_name": feed_name,
                    "auto_generated": True
                }
            )
            seller = await seller_repo.create(seller_model)
        
        return seller.id
    
    async def register_feed(self, name: str, url: str, feed_type: str = "json", 
                           config: Dict[str, Any] = None) -> str:
        """Register a new external feed."""
        feed_id = str(uuid.uuid4())
        
        async with db_manager.get_session() as session:
            feed_repo = ExternalFeedRepository(session)
            await feed_repo.create(feed_id, name, url, feed_type, config or {})
        
        logger.info(f"Registered new feed: {name} ({feed_id})")
        return feed_id
    
    async def list_feeds(self) -> List[Dict[str, Any]]:
        """List all registered feeds."""
        async with db_manager.get_session() as session:
            feed_repo = ExternalFeedRepository(session)
            feeds = await feed_repo.list_active()
            
            return [
                {
                    "id": feed.id,
                    "name": feed.name,
                    "url": feed.url,
                    "feed_type": feed.feed_type,
                    "last_fetched": feed.last_fetched.isoformat() if feed.last_fetched else None,
                    "last_success": feed.last_success.isoformat() if feed.last_success else None,
                    "status": feed.status
                }
                for feed in feeds
            ]
    
    async def ingest_all_feeds(self) -> List[Dict[str, Any]]:
        """Ingest all active feeds."""
        async with db_manager.get_session() as session:
            feed_repo = ExternalFeedRepository(session)
            feeds = await feed_repo.list_active()
        
        results = []
        for feed in feeds:
            try:
                result = await self.ingest_feed(feed.id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to ingest feed {feed.name}: {e}")
                results.append({
                    "feed_id": feed.id,
                    "feed_name": feed.name,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return results


# Global federation service instance
federation_service = FederationService()
