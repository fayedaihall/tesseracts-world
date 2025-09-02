#!/usr/bin/env python3
"""
Tesseracts World Demo Script

This script demonstrates the key capabilities of Tesseracts World
by running through various use cases and scenarios.
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_api_connectivity(base_url: str = "http://localhost:8000"):
    """Test basic API connectivity"""
    print("🔍 Testing API connectivity...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                print("✅ API is running and accessible")
                return True
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Could not connect to API: {e}")
        return False

async def demo_movement_requests(base_url: str = "http://localhost:8000"):
    """Demonstrate movement request functionality"""
    print("\\n📋 Testing Movement Requests...")
    
    headers = {"Authorization": "Bearer tesseracts_demo_key_12345"}
    
    # Test locations (San Francisco area)
    locations = {
        "downtown": {"latitude": 37.7749, "longitude": -122.4194},
        "mission": {"latitude": 37.7599, "longitude": -122.4148},
        "soma": {"latitude": 37.7849, "longitude": -122.4094}
    }
    
    async with httpx.AsyncClient() as client:
        
        # Test delivery request
        print("  🚚 Testing delivery request...")
        delivery_request = {
            "service_type": "delivery",
            "pickup_location": locations["downtown"],
            "dropoff_location": locations["mission"],
            "priority": "normal",
            "package_details": {
                "weight_kg": 2.5,
                "fragile": False
            }
        }
        
        response = await client.post(
            f"{base_url}/api/v1/movement/request",
            json=delivery_request,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"    ✅ Got {len(data['quotes'])} delivery quotes")
            
            # Show quote details
            for i, quote in enumerate(data["quotes"][:3], 1):
                print(f"      {i}. {quote['provider_id']}: ${quote['estimated_cost']} in {quote['estimated_duration_minutes']}min")
            
            # Accept the recommended quote
            if data["quotes"] and data.get("recommended_quote_id"):
                print("  📝 Accepting recommended quote...")
                
                accept_response = await client.post(
                    f"{base_url}/api/v1/movement/accept?quote_id={data['recommended_quote_id']}",
                    json=delivery_request,
                    headers=headers
                )
                
                if accept_response.status_code == 200:
                    job = accept_response.json()
                    print(f"    ✅ Job created: {job['id']}")
                    
                    # Track job status
                    await demo_job_tracking(client, job['id'], base_url, headers)
                    
                else:
                    print(f"    ❌ Failed to accept quote: {accept_response.text}")
        else:
            print(f"    ❌ Delivery request failed: {response.text}")
        
        # Test rideshare request (might not have providers)
        print("  🚗 Testing rideshare request...")
        rideshare_request = {
            "service_type": "rideshare",
            "pickup_location": locations["soma"],
            "dropoff_location": locations["downtown"],
            "priority": "high"
        }
        
        response = await client.post(
            f"{base_url}/api/v1/movement/request",
            json=rideshare_request,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"    ✅ Got {len(data['quotes'])} rideshare quotes")
        else:
            print(f"    ⚠️  Rideshare request returned: {response.status_code}")

async def demo_job_tracking(client, job_id: str, base_url: str, headers: dict):
    """Demonstrate job tracking capabilities"""
    print(f"  📍 Tracking job {job_id[:8]}...")
    
    for i in range(3):
        await asyncio.sleep(1)
        
        # Get job status
        status_response = await client.get(
            f"{base_url}/api/v1/jobs/{job_id}/status",
            headers=headers
        )
        
        if status_response.status_code == 200:
            status = status_response.json()
            print(f"    Status: {status['status']} - {status.get('message', '')}")
            
            # Get location
            track_response = await client.get(
                f"{base_url}/api/v1/jobs/{job_id}/track",
                headers=headers
            )
            
            if track_response.status_code == 200:
                track_data = track_response.json()
                if track_data.get('location'):
                    loc = track_data['location']
                    print(f"    Location: ({loc['latitude']:.4f}, {loc['longitude']:.4f})")
        
        if i < 2:  # Don't sleep after last iteration
            await asyncio.sleep(2)

async def demo_worker_availability(base_url: str = "http://localhost:8000"):
    """Demonstrate worker availability queries"""
    print("\\n👷 Testing Worker Availability...")
    
    headers = {"Authorization": "Bearer tesseracts_demo_key_12345"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/api/v1/workers",
            params={
                "latitude": 37.7749,
                "longitude": -122.4194,
                "service_type": "delivery",
                "radius_km": 20
            },
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['count']} available workers")
            
            # Show worker details
            for worker in data["workers"][:5]:
                vehicle = worker.get("vehicle_type", "Unknown")
                rating = worker.get("rating", "N/A")
                distance = worker.get("distance_km", 0)
                print(f"  • {worker['name']} ({vehicle}) - {rating}⭐ - {distance:.1f}km away")
        else:
            print(f"❌ Worker availability check failed: {response.text}")

async def demo_analytics(base_url: str = "http://localhost:8000"):
    """Demonstrate analytics capabilities"""
    print("\\n📊 Testing Analytics...")
    
    headers = {"Authorization": "Bearer tesseracts_demo_key_12345"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/api/v1/analytics",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Analytics data retrieved:")
            print(f"  • Total jobs: {data['total_jobs']}")
            print(f"  • Active providers: {data['active_providers']}")
            print(f"  • Average cost: ${data['average_cost_usd']}")
            print(f"  • Cached quotes: {data['total_quotes_cached']}")
            
            if data.get("provider_health"):
                print("  • Provider health:")
                for provider, healthy in data["provider_health"].items():
                    status = "🟢 Healthy" if healthy else "🔴 Unhealthy"
                    print(f"    - {provider}: {status}")
        else:
            print(f"❌ Analytics request failed: {response.text}")

async def demo_health_check(base_url: str = "http://localhost:8000"):
    """Demonstrate health check"""
    print("\\n🏥 Testing Health Check...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/v1/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System status: {data['status']}")
            print(f"  • Healthy providers: {data['healthy_providers']}/{data['total_providers']}")
        else:
            print(f"❌ Health check failed: {response.text}")

async def run_full_demo():
    """Run the complete Tesseracts World demonstration"""
    
    print("🌍 Tesseracts World - Universal API for Movement")
    print("Demo Script")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Test basic connectivity
    if not await test_api_connectivity(base_url):
        print("\\n❌ Could not connect to API. Make sure the server is running:")
        print("   python run.py")
        return
    
    # Run demo scenarios
    await demo_health_check(base_url)
    await demo_movement_requests(base_url)
    await demo_worker_availability(base_url)
    await demo_analytics(base_url)
    
    print("\\n" + "=" * 60)
    print("🎉 Demo completed successfully!")
    print("\\n💡 Next steps:")
    print("  • Explore the interactive API docs at http://localhost:8000/docs")
    print("  • Run the example applications:")
    print("    - python examples/rideshare_aggregator.py")
    print("    - python examples/delivery_orchestrator.py")
    print("  • Check out the README.md for more integration examples")

if __name__ == "__main__":
    asyncio.run(run_full_demo())
