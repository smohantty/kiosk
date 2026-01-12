"""
Mock Menu Agent

Simulates the Menu Agent for testing NATS communication.
Responds to menu search and details requests.
"""

import asyncio
from dataclasses import asdict

from common.client import KioskNATSClient, NATSConfig
from common.message import NATSMessage, create_response


# Mock menu database
MOCK_MENU = [
    {
        "id": 101,
        "name": "Volcano Burger",
        "price": 12.99,
        "image": "/img/volcano_burger.png",
        "tags": ["spicy", "popular", "beef"],
        "available": True,
        "description": "Spicy beef patty with jalapeños and habanero sauce",
        "calories": 850,
        "allergens": ["gluten", "dairy"]
    },
    {
        "id": 102,
        "name": "Classic Cheeseburger",
        "price": 9.99,
        "image": "/img/classic_burger.png",
        "tags": ["popular", "beef"],
        "available": True,
        "description": "Classic beef patty with cheddar cheese",
        "calories": 650,
        "allergens": ["gluten", "dairy"]
    },
    {
        "id": 103,
        "name": "Veggie Delight",
        "price": 10.99,
        "image": "/img/veggie_burger.png",
        "tags": ["vegetarian", "healthy"],
        "available": True,
        "description": "Plant-based patty with fresh vegetables",
        "calories": 450,
        "allergens": ["gluten", "soy"]
    },
    {
        "id": 201,
        "name": "Crispy Fries",
        "price": 3.99,
        "image": "/img/fries.png",
        "tags": ["side", "popular"],
        "available": True,
        "description": "Golden crispy fries",
        "calories": 320,
        "allergens": []
    },
    {
        "id": 301,
        "name": "Iced Cola",
        "price": 2.49,
        "image": "/img/cola.png",
        "tags": ["drink", "cold"],
        "available": True,
        "description": "Refreshing cola with ice",
        "calories": 140,
        "allergens": []
    },
]


class MockMenuAgent:
    """Mock Menu Agent that responds to search and details requests."""
    
    def __init__(self):
        self.client = KioskNATSClient(
            config=NATSConfig(name="mock-menu-agent")
        )
    
    async def start(self):
        """Start the mock agent."""
        await self.client.connect()
        
        # Register handlers for menu commands
        await self.client.reply_handler(
            "kiosk.agent.menu.search",
            self.handle_search,
            queue="menu-agents"  # Queue group for load balancing
        )
        
        await self.client.reply_handler(
            "kiosk.agent.menu.details",
            self.handle_details,
            queue="menu-agents"
        )
        
        await self.client.reply_handler(
            "kiosk.agent.menu.availability",
            self.handle_availability,
            queue="menu-agents"
        )
        
        print("\n🍔 Mock Menu Agent ready!\n")
        await self.client.run_forever()
    
    async def handle_search(self, request: NATSMessage) -> NATSMessage:
        """Handle menu search requests."""
        query = request.payload.get("query", "").lower()
        tags = request.payload.get("tags", [])
        dietary_filters = request.payload.get("dietary_filters", [])
        limit = request.payload.get("limit", 10)
        
        # Filter items
        results = []
        for item in MOCK_MENU:
            # Match query in name or description
            if query and query not in item["name"].lower() and query not in item["description"].lower():
                continue
            
            # Match tags
            if tags and not any(tag in item["tags"] for tag in tags):
                continue
            
            # Match dietary filters
            if dietary_filters:
                if "vegetarian" in dietary_filters and "vegetarian" not in item["tags"]:
                    continue
            
            results.append({
                "id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "image": item["image"],
                "tags": item["tags"],
                "available": item["available"]
            })
            
            if len(results) >= limit:
                break
        
        return create_response(
            status="success",
            payload={
                "items": results,
                "total_matches": len(results)
            },
            original_msg=request
        )
    
    async def handle_details(self, request: NATSMessage) -> NATSMessage:
        """Handle item details requests."""
        item_id = request.payload.get("item_id")
        
        for item in MOCK_MENU:
            if item["id"] == item_id:
                return create_response(
                    status="success",
                    payload={"item": item},
                    original_msg=request
                )
        
        return create_response(
            status="error",
            payload={
                "error_code": "ITEM_NOT_FOUND",
                "error_message": f"Item {item_id} not found"
            },
            original_msg=request
        )
    
    async def handle_availability(self, request: NATSMessage) -> NATSMessage:
        """Handle availability check requests."""
        item_id = request.payload.get("item_id")
        
        for item in MOCK_MENU:
            if item["id"] == item_id:
                return create_response(
                    status="success",
                    payload={"item_id": item_id, "available": item["available"]},
                    original_msg=request
                )
        
        return create_response(
            status="error",
            payload={
                "error_code": "ITEM_NOT_FOUND",
                "error_message": f"Item {item_id} not found"
            },
            original_msg=request
        )


async def main():
    agent = MockMenuAgent()
    try:
        await agent.start()
    except KeyboardInterrupt:
        print("\n👋 Shutting down Menu Agent...")


if __name__ == "__main__":
    asyncio.run(main())
