#!/usr/bin/env python3
"""
Example: Delivery Orchestration Platform

This demonstrates how an e-commerce platform could integrate Tesseracts World
to dynamically route orders through the best available courier services.
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Dict, Any

class DeliveryOrchestrator:
    """Example delivery orchestrator using Tesseracts World API"""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def find_fastest_delivery(
        self,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        package_weight_kg: float = 1.0,
        is_fragile: bool = False
    ) -> List[Dict[str, Any]]:
        """Find the fastest delivery options"""
        
        request_data = {
            "service_type": "delivery",
            "pickup_location": {
                "latitude": pickup_lat,
                "longitude": pickup_lng
            },
            "dropoff_location": {
                "latitude": dropoff_lat,
                "longitude": dropoff_lng
            },
            "priority": "high",  # Prioritize speed
            "package_details": {
                "weight_kg": package_weight_kg,
                "fragile": is_fragile
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/movement/request",
                json=request_data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._format_delivery_options(data["quotes"])
            else:
                print(f"Error getting delivery options: {response.text}")
                return []
                
        except Exception as e:
            print(f"Error finding delivery options: {e}")
            return []
    
    async def find_cheapest_delivery(
        self,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        package_weight_kg: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Find the most cost-effective delivery options"""
        
        request_data = {
            "service_type": "delivery",
            "pickup_location": {
                "latitude": pickup_lat,
                "longitude": pickup_lng
            },
            "dropoff_location": {
                "latitude": dropoff_lat,
                "longitude": dropoff_lng
            },
            "priority": "low",  # Prioritize cost
            "package_details": {
                "weight_kg": package_weight_kg
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/movement/request",
                json=request_data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                # Sort by cost
                quotes = sorted(data["quotes"], key=lambda q: float(q["estimated_cost"]))
                return self._format_delivery_options(quotes)
            else:
                print(f"Error getting delivery options: {response.text}")
                return []
                
        except Exception as e:
            print(f"Error finding delivery options: {e}")
            return []
    
    def _format_delivery_options(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format quotes into user-friendly delivery options"""
        delivery_options = []
        
        for quote in quotes:
            option = {
                "quote_id": quote["quote_id"],
                "provider": quote["provider_id"].replace("local_", "").title(),
                "estimated_cost": f"${quote['estimated_cost']}",
                "pickup_time": quote["estimated_pickup_time"],
                "delivery_time": quote["estimated_delivery_time"],
                "duration_minutes": quote["estimated_duration_minutes"],
                "courier_info": {
                    "name": quote.get("worker_info", {}).get("name", "Unknown"),
                    "rating": quote.get("worker_info", {}).get("rating", "N/A"),
                    "vehicle": quote.get("worker_info", {}).get("vehicle", {}).get("type", "Unknown")
                } if quote.get("worker_info") else None
            }
            delivery_options.append(option)
        
        return delivery_options
    
    async def schedule_delivery(
        self, 
        quote_id: str, 
        pickup_lat: float, 
        pickup_lng: float,
        dropoff_lat: float, 
        dropoff_lng: float,
        customer_info: Dict[str, str]
    ) -> Dict[str, Any]:
        """Schedule a delivery using a specific quote"""
        
        request_data = {
            "service_type": "delivery",
            "pickup_location": {
                "latitude": pickup_lat,
                "longitude": pickup_lng
            },
            "dropoff_location": {
                "latitude": dropoff_lat,
                "longitude": dropoff_lng
            },
            "contact_info": customer_info
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/movement/accept",
                params={"quote_id": quote_id},
                json=request_data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                job_data = response.json()
                return {
                    "delivery_id": job_data["id"],
                    "status": job_data["status"],
                    "provider": job_data["provider_id"],
                    "courier": job_data.get("assigned_worker", {}).get("name", "Unknown"),
                    "tracking_url": f"{self.base_url}/track/{job_data['id']}"
                }
            else:
                raise Exception(f"Delivery scheduling failed: {response.text}")
                
        except Exception as e:
            print(f"Error scheduling delivery: {e}")
            raise
    
    async def track_delivery(self, delivery_id: str) -> Dict[str, Any]:
        """Track a delivery in real-time"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/jobs/{delivery_id}/track",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Tracking failed: {response.text}")
                
        except Exception as e:
            print(f"Error tracking delivery: {e}")
            raise
    
    async def batch_schedule_deliveries(
        self, 
        deliveries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Schedule multiple deliveries efficiently"""
        
        results = []
        
        # Process deliveries concurrently
        tasks = []
        for delivery in deliveries:
            task = self._process_single_delivery(delivery)
            tasks.append(task)
        
        delivery_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(delivery_results):
            if isinstance(result, Exception):
                results.append({
                    "order_id": deliveries[i].get("order_id"),
                    "status": "failed",
                    "error": str(result)
                })
            else:
                results.append(result)
        
        return results
    
    async def _process_single_delivery(self, delivery: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single delivery from the batch"""
        
        # Get fastest delivery option
        options = await self.find_fastest_delivery(
            pickup_lat=delivery["pickup_lat"],
            pickup_lng=delivery["pickup_lng"],
            dropoff_lat=delivery["dropoff_lat"],
            dropoff_lng=delivery["dropoff_lng"],
            package_weight_kg=delivery.get("weight_kg", 1.0),
            is_fragile=delivery.get("fragile", False)
        )
        
        if not options:
            raise Exception("No delivery options available")
        
        # Book the best option
        best_option = options[0]
        booking = await self.schedule_delivery(
            quote_id=best_option["quote_id"],
            pickup_lat=delivery["pickup_lat"],
            pickup_lng=delivery["pickup_lng"],
            dropoff_lat=delivery["dropoff_lat"],
            dropoff_lng=delivery["dropoff_lng"],
            customer_info=delivery.get("customer_info", {})
        )
        
        return {
            "order_id": delivery.get("order_id"),
            "delivery_id": booking["delivery_id"],
            "provider": booking["provider"],
            "courier": booking["courier"],
            "status": "scheduled",
            "tracking_url": booking["tracking_url"]
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

# Example usage
async def demo_ecommerce_integration():
    """Demonstrate how an e-commerce platform might integrate delivery orchestration"""
    
    orchestrator = DeliveryOrchestrator("tesseracts_demo_key_12345")
    
    print("📦 E-commerce Delivery Orchestration Demo")
    print("=" * 50)
    
    try:
        # E-commerce warehouse location
        warehouse_lat, warehouse_lng = 37.7849, -122.4094  # San Francisco warehouse
        
        # Customer locations for different orders
        customers = [
            {"lat": 37.7849, "lng": -122.4094, "name": "Customer A"},
            {"lat": 37.7749, "lng": -122.4194, "name": "Customer B"},
            {"lat": 37.7649, "lng": -122.4294, "name": "Customer C"}
        ]
        
        print("🔍 Finding optimal delivery options for 3 orders...")
        
        # Process each order
        for i, customer in enumerate(customers, 1):
            print(f"\\n📋 Order {i} to {customer['name']}:")
            
            # Find fastest delivery
            fastest_options = await orchestrator.find_fastest_delivery(
                pickup_lat=warehouse_lat,
                pickup_lng=warehouse_lng,
                dropoff_lat=customer["lat"],
                dropoff_lng=customer["lng"],
                package_weight_kg=2.5
            )
            
            # Find cheapest delivery
            cheapest_options = await orchestrator.find_cheapest_delivery(
                pickup_lat=warehouse_lat,
                pickup_lng=warehouse_lng,
                dropoff_lat=customer["lat"],
                dropoff_lng=customer["lng"],
                package_weight_kg=2.5
            )
            
            if fastest_options:
                fastest = fastest_options[0]
                print(f"   🚀 Fastest: {fastest['provider']} - {fastest['estimated_cost']} in {fastest['duration_minutes']}min")
            
            if cheapest_options:
                cheapest = cheapest_options[0]
                print(f"   💰 Cheapest: {cheapest['provider']} - {cheapest['estimated_cost']} in {cheapest['duration_minutes']}min")
            
            # Book the fastest option for demonstration
            if fastest_options:
                print(f"   📅 Booking fastest option...")
                booking = await orchestrator.schedule_delivery(
                    quote_id=fastest_options[0]["quote_id"],
                    pickup_lat=warehouse_lat,
                    pickup_lng=warehouse_lng,
                    dropoff_lat=customer["lat"],
                    dropoff_lng=customer["lng"],
                    customer_info={"name": customer["name"], "phone": "+15551234567"}
                )
                
                print(f"   ✅ Scheduled! Delivery ID: {booking['delivery_id']}")
                print(f"   📱 Tracking: {booking['tracking_url']}")
        
        # Demonstrate batch processing
        print(f"\\n🔄 Batch Processing Demo:")
        batch_deliveries = [
            {
                "order_id": "ORD001",
                "pickup_lat": warehouse_lat,
                "pickup_lng": warehouse_lng,
                "dropoff_lat": 37.7849,
                "dropoff_lng": -122.4094,
                "weight_kg": 1.5,
                "customer_info": {"name": "Batch Customer 1"}
            },
            {
                "order_id": "ORD002", 
                "pickup_lat": warehouse_lat,
                "pickup_lng": warehouse_lng,
                "dropoff_lat": 37.7749,
                "dropoff_lng": -122.4194,
                "weight_kg": 3.0,
                "customer_info": {"name": "Batch Customer 2"}
            }
        ]
        
        batch_results = await orchestrator.batch_schedule_deliveries(batch_deliveries)
        
        print(f"📊 Batch Results:")
        for result in batch_results:
            if result["status"] == "scheduled":
                print(f"   ✅ {result['order_id']}: {result['provider']} courier assigned")
            else:
                print(f"   ❌ {result['order_id']}: {result.get('error', 'Failed')}")
    
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    finally:
        await orchestrator.close()

if __name__ == "__main__":
    asyncio.run(demo_ecommerce_integration())
