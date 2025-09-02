#!/usr/bin/env python3
"""
Example: Rideshare Aggregator App

This demonstrates how a hotel or travel app could integrate Tesseracts World
to offer guests access to all local rideshare options through one interface.
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Dict, Any

class RideshareAggregator:
    """Example rideshare aggregator using Tesseracts World API"""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def find_rides(
        self, 
        pickup_lat: float, 
        pickup_lng: float,
        dropoff_lat: float, 
        dropoff_lng: float,
        passenger_count: int = 1
    ) -> List[Dict[str, Any]]:
        """Find available rides from all providers"""
        
        request_data = {
            "service_type": "rideshare",
            "pickup_location": {
                "latitude": pickup_lat,
                "longitude": pickup_lng
            },
            "dropoff_location": {
                "latitude": dropoff_lat,
                "longitude": dropoff_lng
            },
            "priority": "normal",
            "special_requirements": {
                "passenger_count": passenger_count
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
                return self._format_ride_options(data["quotes"])
            else:
                print(f"Error getting rides: {response.text}")
                return []
                
        except Exception as e:
            print(f"Error finding rides: {e}")
            return []
    
    def _format_ride_options(self, quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format quotes into user-friendly ride options"""
        ride_options = []
        
        for quote in quotes:
            option = {
                "quote_id": quote["quote_id"],
                "provider": quote["provider_id"].replace("local_", "").title(),
                "estimated_cost": f"${quote['estimated_cost']}",
                "pickup_time": quote["estimated_pickup_time"],
                "arrival_time": quote["estimated_delivery_time"],
                "duration_minutes": quote["estimated_duration_minutes"],
                "driver_info": {
                    "name": quote.get("worker_info", {}).get("name", "Unknown"),
                    "rating": quote.get("worker_info", {}).get("rating", "N/A"),
                    "vehicle": quote.get("worker_info", {}).get("vehicle", {}).get("type", "Unknown")
                } if quote.get("worker_info") else None
            }
            ride_options.append(option)
        
        return ride_options
    
    async def book_ride(self, quote_id: str, pickup_lat: float, pickup_lng: float,
                       dropoff_lat: float, dropoff_lng: float) -> Dict[str, Any]:
        """Book a ride using a specific quote"""
        
        request_data = {
            "service_type": "rideshare",
            "pickup_location": {
                "latitude": pickup_lat,
                "longitude": pickup_lng
            },
            "dropoff_location": {
                "latitude": dropoff_lat,
                "longitude": dropoff_lng
            }
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
                    "job_id": job_data["id"],
                    "status": job_data["status"],
                    "provider": job_data["provider_id"],
                    "driver": job_data.get("assigned_worker", {}).get("name", "Unknown"),
                    "pickup_location": job_data["pickup_location"],
                    "dropoff_location": job_data["dropoff_location"]
                }
            else:
                raise Exception(f"Booking failed: {response.text}")
                
        except Exception as e:
            print(f"Error booking ride: {e}")
            raise
    
    async def track_ride(self, job_id: str) -> Dict[str, Any]:
        """Track a ride in real-time"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/jobs/{job_id}/track",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Tracking failed: {response.text}")
                
        except Exception as e:
            print(f"Error tracking ride: {e}")
            raise
    
    async def get_ride_status(self, job_id: str) -> Dict[str, Any]:
        """Get current ride status"""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/jobs/{job_id}/status",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Status check failed: {response.text}")
                
        except Exception as e:
            print(f"Error getting ride status: {e}")
            raise
    
    async def cancel_ride(self, job_id: str) -> bool:
        """Cancel a ride"""
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/v1/jobs/{job_id}",
                headers=self.headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error cancelling ride: {e}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

# Example usage
async def demo_hotel_integration():
    """Demonstrate how a hotel app might integrate rideshare aggregation"""
    
    aggregator = RideshareAggregator("tesseracts_demo_key_12345")
    
    print("🏨 Hotel Guest Rideshare Integration Demo")
    print("=" * 50)
    
    try:
        # Guest wants to go from hotel to airport
        hotel_lat, hotel_lng = 37.7749, -122.4194  # San Francisco hotel
        airport_lat, airport_lng = 37.6213, -122.3790  # SFO Airport
        
        print(f"🔍 Finding rides from hotel to SFO Airport...")
        rides = await aggregator.find_rides(
            pickup_lat=hotel_lat,
            pickup_lng=hotel_lng,
            dropoff_lat=airport_lat,
            dropoff_lng=airport_lng,
            passenger_count=2
        )
        
        if not rides:
            print("❌ No rides available")
            return
        
        print(f"✅ Found {len(rides)} ride options:")
        for i, ride in enumerate(rides, 1):
            print(f"\\n{i}. {ride['provider']}")
            print(f"   Cost: {ride['estimated_cost']}")
            print(f"   Pickup: {ride['pickup_time']}")
            print(f"   Duration: {ride['duration_minutes']} minutes")
            if ride['driver_info']:
                print(f"   Driver: {ride['driver_info']['name']} ({ride['driver_info']['rating']}⭐)")
        
        # Book the first available ride
        if rides:
            selected_ride = rides[0]
            print(f"\\n🚗 Booking ride with {selected_ride['provider']}...")
            
            booking = await aggregator.book_ride(
                quote_id=selected_ride["quote_id"],
                pickup_lat=hotel_lat,
                pickup_lng=hotel_lng,
                dropoff_lat=airport_lat,
                dropoff_lng=airport_lng
            )
            
            print(f"✅ Ride booked! Job ID: {booking['job_id']}")
            print(f"   Driver: {booking['driver']}")
            print(f"   Status: {booking['status']}")
            
            # Track the ride for a few updates
            print(f"\\n📍 Tracking ride...")
            for i in range(3):
                await asyncio.sleep(2)
                status = await aggregator.get_ride_status(booking['job_id'])
                print(f"   Status: {status['status']} - {status.get('message', '')}")
                
                location = await aggregator.track_ride(booking['job_id'])
                if location and location['location']:
                    loc = location['location']
                    print(f"   Location: ({loc['latitude']:.4f}, {loc['longitude']:.4f})")
    
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    finally:
        await aggregator.close()

if __name__ == "__main__":
    asyncio.run(demo_hotel_integration())
