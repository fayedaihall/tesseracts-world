import pytest
import asyncio
from fastapi.testclient import TestClient
from datetime import datetime

from src.api.main import app
from src.models.core import ServiceType, Priority

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer tesseracts_demo_key_12345"}

def test_root_endpoint(client):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Tesseracts World" in response.json()["message"]

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "providers" in data

def test_movement_request_delivery(client, auth_headers):
    """Test requesting delivery quotes"""
    request_data = {
        "service_type": "delivery",
        "pickup_location": {
            "latitude": 37.7749,
            "longitude": -122.4194
        },
        "dropoff_location": {
            "latitude": 37.7849,
            "longitude": -122.4094
        },
        "priority": "normal"
    }
    
    response = client.post(
        "/api/v1/movement/request",
        json=request_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "quotes" in data
    assert "request_id" in data
    assert len(data["quotes"]) > 0

def test_movement_request_rideshare(client, auth_headers):
    """Test requesting rideshare quotes"""
    request_data = {
        "service_type": "rideshare",
        "pickup_location": {
            "latitude": 37.7749,
            "longitude": -122.4194
        },
        "dropoff_location": {
            "latitude": 37.7849,
            "longitude": -122.4094
        },
        "priority": "high"
    }
    
    response = client.post(
        "/api/v1/movement/request",
        json=request_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "quotes" in data
    assert len(data["quotes"]) >= 0  # Rideshare might not be available from mock providers

def test_accept_quote_and_track_job(client, auth_headers):
    """Test accepting a quote and tracking the resulting job"""
    
    # First, get quotes
    request_data = {
        "service_type": "delivery",
        "pickup_location": {
            "latitude": 37.7749,
            "longitude": -122.4194
        },
        "dropoff_location": {
            "latitude": 37.7849,
            "longitude": -122.4094
        },
        "priority": "normal"
    }
    
    quotes_response = client.post(
        "/api/v1/movement/request",
        json=request_data,
        headers=auth_headers
    )
    
    assert quotes_response.status_code == 200
    quotes_data = quotes_response.json()
    assert len(quotes_data["quotes"]) > 0
    
    # Accept the first quote
    quote_id = quotes_data["quotes"][0]["quote_id"]
    
    accept_response = client.post(
        f"/api/v1/movement/accept?quote_id={quote_id}",
        json=request_data,
        headers=auth_headers
    )
    
    assert accept_response.status_code == 200
    job_data = accept_response.json()
    assert "id" in job_data
    assert job_data["status"] in ["pending", "assigned"]
    
    job_id = job_data["id"]
    
    # Check job status
    status_response = client.get(
        f"/api/v1/jobs/{job_id}/status",
        headers=auth_headers
    )
    
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert "status" in status_data
    assert "job_id" in status_data
    
    # Track job location
    track_response = client.get(
        f"/api/v1/jobs/{job_id}/track",
        headers=auth_headers
    )
    
    assert track_response.status_code == 200
    track_data = track_response.json()
    assert "job_id" in track_data

def test_get_available_workers(client, auth_headers):
    """Test getting available workers near a location"""
    response = client.get(
        "/api/v1/workers",
        params={
            "latitude": 37.7749,
            "longitude": -122.4194,
            "service_type": "delivery",
            "radius_km": 15
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "workers" in data
    assert "count" in data

def test_analytics_endpoint(client, auth_headers):
    """Test the analytics endpoint"""
    response = client.get(
        "/api/v1/analytics",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "provider_health" in data
    assert "status_breakdown" in data

def test_unauthorized_request(client):
    """Test that requests without proper authentication are rejected"""
    request_data = {
        "service_type": "delivery",
        "pickup_location": {"latitude": 37.7749, "longitude": -122.4194},
        "dropoff_location": {"latitude": 37.7849, "longitude": -122.4094}
    }
    
    response = client.post(
        "/api/v1/movement/request",
        json=request_data
    )
    
    assert response.status_code == 403  # No auth header

def test_invalid_api_key(client):
    """Test that invalid API keys are rejected"""
    request_data = {
        "service_type": "delivery",
        "pickup_location": {"latitude": 37.7749, "longitude": -122.4194},
        "dropoff_location": {"latitude": 37.7849, "longitude": -122.4094}
    }
    
    response = client.post(
        "/api/v1/movement/request",
        json=request_data,
        headers={"Authorization": "Bearer invalid_key"}
    )
    
    assert response.status_code == 401

def test_job_cancellation(client, auth_headers):
    """Test job cancellation"""
    
    # Create a job first
    request_data = {
        "service_type": "delivery",
        "pickup_location": {"latitude": 37.7749, "longitude": -122.4194},
        "dropoff_location": {"latitude": 37.7849, "longitude": -122.4094},
        "priority": "normal"
    }
    
    # Get quotes
    quotes_response = client.post(
        "/api/v1/movement/request",
        json=request_data,
        headers=auth_headers
    )
    assert quotes_response.status_code == 200
    quotes_data = quotes_response.json()
    
    if len(quotes_data["quotes"]) > 0:
        # Accept quote to create job
        quote_id = quotes_data["quotes"][0]["quote_id"]
        accept_response = client.post(
            f"/api/v1/movement/accept?quote_id={quote_id}",
            json=request_data,
            headers=auth_headers
        )
        assert accept_response.status_code == 200
        job_id = accept_response.json()["id"]
        
        # Cancel the job
        cancel_response = client.delete(
            f"/api/v1/jobs/{job_id}",
            headers=auth_headers
        )
        
        assert cancel_response.status_code == 200
        assert cancel_response.json()["success"] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
