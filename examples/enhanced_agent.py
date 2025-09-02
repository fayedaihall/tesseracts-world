#!/usr/bin/env python3
"""
Enhanced Tesseracts World Agent - Demonstrates decentralized commerce with:
- Database persistence
- External catalog federation 
- Multi-seller basket optimization
- Flow blockchain escrow integration
"""

import asyncio
import aiohttp
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ShoppingItem:
    """Item to purchase"""
    query: str
    quantity: int
    max_price: Optional[float] = None
    preferred_category: Optional[str] = None

@dataclass
class BasketOption:
    """Optimized basket option"""
    items: List[Dict[str, Any]]  # Products with quantities
    sellers: Dict[str, str]  # seller_id -> seller_name
    total_cost: float
    total_delivery_cost: float
    total_time_estimate: float
    consolidated_deliveries: int
    optimization_score: float

class EnhancedTesseractsAgent:
    def __init__(self, api_url: str = "http://localhost:8000", api_key: str = "demo-key"):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.buyer_did = "did:key:buyer123"
        
        # Delivery address
        self.delivery_address = {
            "name": "Agent Test User",
            "phone": "+1-555-0100",
            "address": "123 Innovation Drive, Tech City, CA 94000",
            "latitude": 37.7749,
            "longitude": -122.4194
        }
    
    async def setup_demo_data(self):
        """Setup demo sellers, products, and external feeds"""
        logger.info("🏗️  Setting up demo data...")
        
        # Register demo sellers
        sellers = [
            {
                "id": "seller_electronics",
                "name": "TechHub Electronics",
                "did": {"method": "did:key", "identifier": "tech_hub_123"},
                "reputation_score": 4.8,
                "metadata": {
                    "website": "https://techhub.example.com",
                    "categories": ["Electronics", "Computers", "Mobile"]
                }
            },
            {
                "id": "seller_books", 
                "name": "BookWorm Central",
                "did": {"method": "did:key", "identifier": "bookworm_456"},
                "reputation_score": 4.9,
                "metadata": {
                    "website": "https://bookworm.example.com",
                    "categories": ["Books", "Education", "Literature"]
                }
            },
            {
                "id": "seller_home",
                "name": "HomeEssentials Co",
                "did": {"method": "did:key", "identifier": "home_essentials_789"},
                "reputation_score": 4.6,
                "metadata": {
                    "website": "https://homeessentials.example.com",
                    "categories": ["Home", "Garden", "Kitchen"]
                }
            }
        ]
        
        for seller in sellers:
            try:
                await self._api_request('POST', '/api/v1/sellers', seller)
            except Exception as e:
                logger.warning(f"Seller registration failed (may already exist): {e}")
        
        # Register demo products
        products = [
            # Electronics
            {
                "id": "laptop_001",
                "seller_id": "seller_electronics",
                "title": "UltraBook Pro 15\"",
                "description": "High-performance laptop for professionals",
                "price": 1299.99,
                "weight_kg": 1.8,
                "categories": ["Electronics", "Computers"],
                "inventory": 25,
                "fulfillment_origin": {"latitude": 37.7849, "longitude": -122.4094, "address": "TechHub Warehouse"}
            },
            {
                "id": "phone_001",
                "seller_id": "seller_electronics", 
                "title": "SmartPhone X Pro",
                "description": "Latest flagship smartphone",
                "price": 899.99,
                "weight_kg": 0.2,
                "categories": ["Electronics", "Mobile"],
                "inventory": 50,
                "fulfillment_origin": {"latitude": 37.7849, "longitude": -122.4094, "address": "TechHub Warehouse"}
            },
            
            # Books
            {
                "id": "book_001",
                "seller_id": "seller_books",
                "title": "Distributed Systems Design",
                "description": "Comprehensive guide to building scalable systems",
                "price": 59.99,
                "weight_kg": 0.8,
                "categories": ["Books", "Technology"],
                "inventory": 100,
                "fulfillment_origin": {"latitude": 37.7649, "longitude": -122.4294, "address": "BookWorm Warehouse"}
            },
            {
                "id": "book_002",
                "seller_id": "seller_books",
                "title": "Blockchain Fundamentals",
                "description": "Understanding decentralized technologies",
                "price": 49.99,
                "weight_kg": 0.6,
                "categories": ["Books", "Technology", "Finance"],
                "inventory": 75,
                "fulfillment_origin": {"latitude": 37.7649, "longitude": -122.4294, "address": "BookWorm Warehouse"}
            },
            
            # Home items
            {
                "id": "coffee_001",
                "seller_id": "seller_home",
                "title": "Premium Coffee Maker",
                "description": "Professional-grade coffee brewing system",
                "price": 249.99,
                "weight_kg": 3.5,
                "categories": ["Home", "Kitchen"],
                "inventory": 30,
                "fulfillment_origin": {"latitude": 37.7549, "longitude": -122.4394, "address": "HomeEssentials Distribution"}
            }
        ]
        
        for product in products:
            try:
                await self._api_request('POST', '/api/v1/products', product)
            except Exception as e:
                logger.warning(f"Product registration failed (may already exist): {e}")
        
        # Register external feed (mock JSON API)
        external_feed = {
            "name": "Global Electronics Feed",
            "url": "https://api.example.com/products.json",  # Mock URL
            "feed_type": "json",
            "config": {
                "field_mapping": {
                    "id": "product_id",
                    "title": "name",
                    "price": "cost"
                },
                "default_seller": "seller_electronics"
            }
        }
        
        try:
            feed_result = await self._api_request('POST', '/api/v1/federation/feeds', external_feed)
            logger.info(f"📡 Registered external feed: {feed_result.get('feed_id')}")
        except Exception as e:
            logger.warning(f"Could not register external feed (expected in demo): {e}")
        
        logger.info("✅ Demo data setup complete")
    
    async def optimize_multi_seller_basket(self, shopping_items: List[ShoppingItem]) -> List[BasketOption]:
        """
        Optimize shopping basket across multiple sellers considering:
        - Product availability and pricing
        - Delivery cost consolidation 
        - Estimated delivery time
        - Overall cost optimization
        """
        logger.info(f"🛒 Optimizing basket with {len(shopping_items)} items...")
        
        # Step 1: Find products for each shopping item
        item_options = {}
        for i, item in enumerate(shopping_items):
            search_params = {
                'q': item.query,
                'limit': 10
            }
            if item.max_price:
                search_params['max_price'] = item.max_price
            
            search_result = await self._api_request('GET', '/api/v1/products/search', params=search_params)
            products = search_result.get('products', [])
            
            # Filter and score products
            suitable_products = []
            for product in products:
                if product['inventory'] >= item.quantity:
                    # Score based on price, rating, availability
                    price_score = min(1.0, (item.max_price or 9999) / product['price']) if item.max_price else 0.8
                    availability_score = min(1.0, product['inventory'] / (item.quantity * 2))
                    
                    overall_score = (price_score * 0.4 + availability_score * 0.3 + 0.3)
                    
                    suitable_products.append({
                        **product,
                        'quantity_needed': item.quantity,
                        'suitability_score': overall_score
                    })
            
            # Sort by suitability score
            suitable_products.sort(key=lambda x: x['suitability_score'], reverse=True)
            item_options[i] = suitable_products[:5]  # Keep top 5 options per item
        
        logger.info(f"🔍 Found product options: {sum(len(opts) for opts in item_options.values())} total")
        
        # Step 2: Generate basket combinations
        basket_options = await self._generate_basket_combinations(item_options, shopping_items)
        
        # Step 3: Evaluate delivery options for each basket
        evaluated_baskets = []
        for basket in basket_options[:10]:  # Limit to top 10 combinations
            try:
                delivery_evaluation = await self._evaluate_basket_delivery(basket)
                basket_option = BasketOption(
                    items=basket['items'],
                    sellers=basket['sellers'],
                    total_cost=basket['total_cost'],
                    total_delivery_cost=delivery_evaluation['total_delivery_cost'],
                    total_time_estimate=delivery_evaluation['total_time_estimate'],
                    consolidated_deliveries=delivery_evaluation['consolidated_deliveries'],
                    optimization_score=self._calculate_optimization_score(basket, delivery_evaluation)
                )
                evaluated_baskets.append(basket_option)
            except Exception as e:
                logger.warning(f"Could not evaluate delivery for basket: {e}")
                continue
        
        # Sort by optimization score
        evaluated_baskets.sort(key=lambda x: x.optimization_score, reverse=True)
        
        logger.info(f"📊 Generated {len(evaluated_baskets)} optimized basket options")
        return evaluated_baskets[:5]  # Return top 5 options
    
    async def _generate_basket_combinations(self, item_options: Dict[int, List], shopping_items: List[ShoppingItem]) -> List[Dict]:
        """Generate feasible basket combinations"""
        # For demo, we'll generate a few good combinations rather than all possible
        combinations = []
        
        # Strategy 1: Best single option per item
        best_combination = {'items': [], 'sellers': {}, 'total_cost': 0}
        for i, item in enumerate(shopping_items):
            if item_options[i]:
                best_product = item_options[i][0]
                best_combination['items'].append(best_product)
                best_combination['sellers'][best_product['seller_id']] = best_product.get('seller_name', best_product['seller_id'])
                best_combination['total_cost'] += best_product['price'] * best_product['quantity_needed']
        
        if best_combination['items']:
            combinations.append(best_combination)
        
        # Strategy 2: Prefer single seller when possible
        seller_grouped = {}
        for i, options in item_options.items():
            for product in options:
                seller_id = product['seller_id']
                if seller_id not in seller_grouped:
                    seller_grouped[seller_id] = []
                seller_grouped[seller_id].append((i, product))
        
        # Find sellers that can fulfill multiple items
        for seller_id, seller_products in seller_grouped.items():
            if len(seller_products) >= 2:  # Can fulfill multiple items
                single_seller_combination = {'items': [], 'sellers': {seller_id: seller_id}, 'total_cost': 0}
                covered_items = set()
                
                for item_idx, product in seller_products:
                    if item_idx not in covered_items:
                        single_seller_combination['items'].append(product)
                        single_seller_combination['total_cost'] += product['price'] * product['quantity_needed']
                        covered_items.add(item_idx)
                
                # Fill remaining items with best options
                for i, item in enumerate(shopping_items):
                    if i not in covered_items and item_options[i]:
                        best_remaining = item_options[i][0]
                        single_seller_combination['items'].append(best_remaining)
                        single_seller_combination['sellers'][best_remaining['seller_id']] = best_remaining['seller_id']
                        single_seller_combination['total_cost'] += best_remaining['price'] * best_remaining['quantity_needed']
                
                combinations.append(single_seller_combination)
        
        return combinations[:20]  # Limit combinations
    
    async def _evaluate_basket_delivery(self, basket: Dict) -> Dict:
        """Evaluate delivery options for a basket"""
        # Group items by seller for delivery consolidation
        seller_groups = {}
        for item in basket['items']:
            seller_id = item['seller_id']
            if seller_id not in seller_groups:
                seller_groups[seller_id] = []
            seller_groups[seller_id].append(item)
        
        total_delivery_cost = 0
        total_time_estimate = 0
        consolidated_deliveries = len(seller_groups)
        
        # For each seller group, estimate delivery cost and time
        for seller_id, items in seller_groups.items():
            # Mock delivery cost calculation (in real system, would query movement API)
            total_weight = sum(item.get('weight_kg', 1.0) * item['quantity_needed'] for item in items)
            base_cost = 5.99 if total_weight < 2 else 12.99
            weight_surcharge = max(0, (total_weight - 5) * 2.50)
            delivery_cost = base_cost + weight_surcharge
            
            total_delivery_cost += delivery_cost
            
            # Estimate delivery time (mock calculation)
            distance_factor = 1.0  # Could calculate based on fulfillment origin
            estimated_hours = 24 + (total_weight * 2) + (distance_factor * 12)
            total_time_estimate = max(total_time_estimate, estimated_hours)  # Parallel deliveries
        
        return {
            'total_delivery_cost': total_delivery_cost,
            'total_time_estimate': total_time_estimate,
            'consolidated_deliveries': consolidated_deliveries
        }
    
    def _calculate_optimization_score(self, basket: Dict, delivery_eval: Dict) -> float:
        """Calculate overall optimization score for basket"""
        # Factors: cost efficiency, delivery consolidation, time
        total_value = basket['total_cost'] + delivery_eval['total_delivery_cost']
        
        # Normalize scores
        cost_score = max(0, 1 - (total_value / 2000))  # Assume $2000 baseline
        consolidation_score = max(0, 1 - (delivery_eval['consolidated_deliveries'] - 1) * 0.3)
        time_score = max(0, 1 - (delivery_eval['total_time_estimate'] - 24) / 48)  # Prefer <24h delivery
        
        # Weighted combination
        return cost_score * 0.4 + consolidation_score * 0.35 + time_score * 0.25
    
    async def execute_optimized_purchase(self, basket_option: BasketOption):
        """Execute the optimized purchase with escrow and delivery"""
        logger.info(f"💳 Executing optimized purchase with {len(basket_option.sellers)} sellers...")
        
        # Group items by seller to create orders
        seller_orders = {}
        for item in basket_option.items:
            seller_id = item['seller_id']
            if seller_id not in seller_orders:
                seller_orders[seller_id] = []
            
            order_item = {
                "product_id": item['id'],
                "title": item['title'],
                "quantity": item['quantity_needed'],
                "unit_price": item['price'],
                "currency": "USD",
                "weight_kg": item.get('weight_kg', 1.0)
            }
            seller_orders[seller_id].append(order_item)
        
        created_orders = []
        
        # Create orders with each seller
        for seller_id, items in seller_orders.items():
            order_request = {
                "seller_id": seller_id,
                "items": items,
                "dropoff": self.delivery_address,
                "buyer_did_identifier": self.buyer_did
            }
            
            try:
                order = await self._api_request('POST', '/api/v1/orders', order_request)
                created_orders.append(order)
                logger.info(f"📦 Created order {order['id']} with {seller_id}")
                
                # Create and fund escrow
                escrow_amount = sum(item['unit_price'] * item['quantity'] for item in items)
                escrow_request = {"amount": escrow_amount, "currency": "USD"}
                
                escrow_result = await self._api_request(
                    'POST', f'/api/v1/orders/{order["id"]}/escrow', escrow_request
                )
                logger.info(f"🔒 Created escrow {escrow_result['escrow_id']} for order {order['id']}")
                
                # Fund escrow
                fund_request = {"escrow_id": escrow_result['escrow_id']}
                await self._api_request(
                    'POST', f'/api/v1/orders/{order["id"]}/escrow/fund', fund_request
                )
                logger.info(f"💰 Funded escrow for order {order['id']}")
                
                # Request delivery quotes
                quotes = await self._api_request(
                    'POST', f'/api/v1/orders/{order["id"]}/delivery/quotes'
                )
                
                if quotes.get('quotes'):
                    # Accept best quote
                    best_quote = min(quotes['quotes'], key=lambda q: q['price'])
                    accept_request = {"quote_id": best_quote['id']}
                    
                    job = await self._api_request(
                        'POST', f'/api/v1/orders/{order["id"]}/delivery/accept', accept_request
                    )
                    logger.info(f"🚚 Booked delivery {job['id']} for order {order['id']}")
                
            except Exception as e:
                logger.error(f"Error processing order with {seller_id}: {e}")
                continue
        
        logger.info(f"✅ Successfully created {len(created_orders)} orders")
        return created_orders
    
    async def demonstrate_federation_ingest(self):
        """Demonstrate external catalog federation"""
        logger.info("📡 Demonstrating federation capabilities...")
        
        try:
            # List registered feeds
            feeds = await self._api_request('GET', '/api/v1/federation/feeds')
            logger.info(f"📋 Found {feeds.get('count', 0)} registered feeds")
            
            # Trigger ingestion of all feeds
            if feeds.get('count', 0) > 0:
                ingest_results = await self._api_request('POST', '/api/v1/federation/ingest-all')
                logger.info(f"🔄 Federation ingest results: {ingest_results.get('count', 0)} feeds processed")
            
        except Exception as e:
            logger.warning(f"Federation demo skipped (expected in local demo): {e}")
    
    async def _api_request(self, method: str, endpoint: str, data: Any = None, params: Dict = None) -> Dict:
        """Make authenticated API request"""
        url = f"{self.api_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            kwargs = {"headers": headers}
            if data:
                kwargs["json"] = data
            if params:
                kwargs["params"] = params
                
            async with session.request(method, url, **kwargs) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"API request failed: {response.status} - {error_text}")
                
                return await response.json()
    
    async def run_enhanced_demo(self):
        """Run complete enhanced agent demonstration"""
        logger.info("🚀 Starting Enhanced Tesseracts World Agent Demo...")
        
        try:
            # Setup demo environment
            await self.setup_demo_data()
            await asyncio.sleep(2)  # Allow data to settle
            
            # Demonstrate federation
            await self.demonstrate_federation_ingest()
            
            # Define shopping list
            shopping_list = [
                ShoppingItem(query="laptop", quantity=1, max_price=1500.0),
                ShoppingItem(query="blockchain book", quantity=2, max_price=60.0),
                ShoppingItem(query="coffee maker", quantity=1, preferred_category="Kitchen")
            ]
            
            logger.info(f"🛍️  Shopping list: {len(shopping_list)} items")
            for i, item in enumerate(shopping_list, 1):
                logger.info(f"  {i}. {item.query} (qty: {item.quantity}, max: ${item.max_price or 'no limit'})")
            
            # Optimize basket across sellers
            basket_options = await self.optimize_multi_seller_basket(shopping_list)
            
            if not basket_options:
                logger.error("❌ No viable basket options found")
                return
            
            # Display optimization results
            logger.info(f"\n📊 OPTIMIZATION RESULTS:")
            for i, option in enumerate(basket_options, 1):
                logger.info(f"\n  Option {i} (Score: {option.optimization_score:.2f}):")
                logger.info(f"    Items: {len(option.items)} products")
                logger.info(f"    Sellers: {len(option.sellers)} ({', '.join(option.sellers.values())})")
                logger.info(f"    Product cost: ${option.total_cost:.2f}")
                logger.info(f"    Delivery cost: ${option.total_delivery_cost:.2f}")
                logger.info(f"    Total cost: ${option.total_cost + option.total_delivery_cost:.2f}")
                logger.info(f"    Estimated delivery: {option.total_time_estimate:.0f} hours")
                logger.info(f"    Delivery consolidation: {option.consolidated_deliveries} shipments")
            
            # Execute best option
            best_option = basket_options[0]
            logger.info(f"\n🎯 Executing best option (Score: {best_option.optimization_score:.2f})...")
            
            orders = await self.execute_optimized_purchase(best_option)
            
            # Summary
            total_orders = len(orders)
            total_cost = best_option.total_cost + best_option.total_delivery_cost
            
            logger.info(f"\n✅ PURCHASE COMPLETE!")
            logger.info(f"   Orders created: {total_orders}")
            logger.info(f"   Total cost: ${total_cost:.2f}")
            logger.info(f"   Sellers involved: {len(best_option.sellers)}")
            logger.info(f"   Estimated delivery: {best_option.total_time_estimate:.0f} hours")
            logger.info(f"   Optimization score: {best_option.optimization_score:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise


async def main():
    """Main entry point"""
    agent = EnhancedTesseractsAgent()
    await agent.run_enhanced_demo()


if __name__ == "__main__":
    asyncio.run(main())
