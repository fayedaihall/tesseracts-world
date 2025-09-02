#!/usr/bin/env python3
"""
Agentic shopper demo: publishes sample sellers/products, searches, creates order,
funds escrow, accepts best delivery quote.
"""

import asyncio
import httpx

BASE_URL = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer tesseracts_demo_key_12345"}

async def ensure_sample_catalog(client: httpx.AsyncClient):
    # Register two sellers
    sellers = [
        {
            "name": "Local Coffee Roasters",
            "website": "https://coffee.local",
            "metadata": {"tags": ["coffee", "grocery"]},
        },
        {
            "name": "Artisan Bakery",
            "website": "https://bakery.local",
            "metadata": {"tags": ["bakery", "fresh"]},
        },
    ]

    seller_ids = []
    for s in sellers:
        r = await client.post(f"{BASE_URL}/api/v1/commerce/sellers", json=s, headers=HEADERS)
        r.raise_for_status()
        seller_ids.append(r.json()["id"])

    # Publish products
    products = [
        {
            "seller_id": seller_ids[0],
            "title": "Single Origin Beans 1kg",
            "description": "Freshly roasted beans",
            "price": 18.5,
            "currency": "USD",
            "inventory": 25,
            "categories": ["grocery", "coffee"],
            "fulfillment_origin": {
                "latitude": 37.775,
                "longitude": -122.418,
                "address": "123 Coffee St, SF"
            }
        },
        {
            "seller_id": seller_ids[1],
            "title": "Sourdough Loaf",
            "description": "Daily fresh sourdough",
            "price": 7.0,
            "currency": "USD",
            "inventory": 40,
            "categories": ["bakery"],
            "fulfillment_origin": {
                "latitude": 37.779,
                "longitude": -122.414,
                "address": "55 Bread Ave, SF"
            }
        }
    ]

    product_ids = []
    for p in products:
        r = await client.post(f"{BASE_URL}/api/v1/commerce/products", json=p, headers=HEADERS)
        r.raise_for_status()
        product_ids.append(r.json()["id"])
    return seller_ids, product_ids

async def agentic_purchase_flow():
    async with httpx.AsyncClient() as client:
        # Ensure catalog present
        seller_ids, product_ids = await ensure_sample_catalog(client)

        # Agent search for "coffee"
        r = await client.get(f"{BASE_URL}/api/v1/commerce/search", params={"q": "coffee"}, headers=HEADERS)
        r.raise_for_status()
        results = r.json()
        if not results:
            print("No products found")
            return
        coffee = results[0]
        print("Found:", coffee["title"], "at", coffee["price"])

        # Build order (deliver to a nearby address)
        create_payload = {
            "seller_id": coffee["seller_id"],
            "items": [
                {
                    "product_id": coffee["id"],
                    "title": coffee["title"],
                    "quantity": 2,
                    "unit_price": coffee["price"],
                    "currency": coffee["currency"],
                }
            ],
            "dropoff": {
                "name": "Agent Buyer",
                "address": "999 Market St, SF",
                "latitude": 37.782,
                "longitude": -122.41
            },
            # MovementRequest base fields
            "service_type": "delivery",
            "pickup_location": {"latitude": coffee["fulfillment_origin"]["latitude"], "longitude": coffee["fulfillment_origin"]["longitude"]},
            "dropoff_location": {"latitude": 37.782, "longitude": -122.41},
            "priority": "normal"
        }

        r = await client.post(f"{BASE_URL}/api/v1/commerce/orders", json=create_payload, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        order = data["order"]
        quotes = data["delivery_quotes"]["quotes"]
        print("Order created:", order["id"], "quotes:", len(quotes))

        # Fund escrow
        r = await client.post(f"{BASE_URL}/api/v1/commerce/orders/{order['id']}/fund", headers=HEADERS)
        r.raise_for_status()
        print("Escrow funded")

        # Accept best quote (first one)
        if quotes:
            best_quote_id = quotes[0]["quote_id"]
            r = await client.post(f"{BASE_URL}/api/v1/commerce/orders/{order['id']}/accept", params={"quote_id": best_quote_id}, headers=HEADERS)
            r.raise_for_status()
            result = r.json()
            print("Delivery booked:", result["job"]["id"]) 

if __name__ == "__main__":
    asyncio.run(agentic_purchase_flow())

