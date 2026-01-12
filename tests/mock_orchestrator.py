"""
Mock Orchestrator

Simulates the Orchestrator for testing NATS communication.
Subscribes to events and sends requests to agents.
"""

import asyncio
from typing import Optional

from common.client import KioskNATSClient, NATSConfig
from common.message import NATSMessage, create_event, create_request


class MockOrchestrator:
    """
    Mock Orchestrator that demonstrates:
    - Subscribing to vision/voice events
    - Sending requests to agents
    - Parallel agent queries
    """
    
    def __init__(self):
        self.client = KioskNATSClient(
            config=NATSConfig(name="mock-orchestrator")
        )
        self.session_id = "test-session-001"
        self.current_state = "idle"
    
    async def start(self):
        """Start the orchestrator."""
        await self.client.connect()
        
        # Subscribe to vision events
        await self.client.subscribe(
            "kiosk.vision.>",
            self.handle_vision_event
        )
        
        # Subscribe to voice events
        await self.client.subscribe(
            "kiosk.voice.>",
            self.handle_voice_event
        )
        
        # Subscribe to input events (from frontend)
        await self.client.subscribe(
            "kiosk.input.>",
            self.handle_input_event
        )
        
        print("\n🧠 Mock Orchestrator ready!\n")
        print("Listening for events...")
        print("=" * 50)
        
        await self.client.run_forever()
    
    async def handle_vision_event(self, msg: NATSMessage, subject: str):
        """Handle vision events."""
        event = msg.payload.get("event")
        
        if event == "person_detected":
            print(f"\n👁️ Vision: Person detected!")
            print(f"   Confidence: {msg.payload.get('confidence', 0):.0%}")
            print(f"   Party size: {msg.payload.get('estimated_party_size', 1)}")
            
            # Transition to attract state
            self.current_state = "attract"
            print(f"   → State: {self.current_state}")
        
        elif event == "person_left":
            print(f"\n👋 Vision: Person left")
            self.current_state = "idle"
            print(f"   → State: {self.current_state}")
    
    async def handle_voice_event(self, msg: NATSMessage, subject: str):
        """Handle voice events."""
        event = msg.payload.get("event")
        
        if event == "transcript":
            text = msg.payload.get("text", "")
            print(f"\n🎤 Voice: \"{text}\"")
            print(f"   Confidence: {msg.payload.get('confidence', 0):.0%}")
            
            # Simple intent detection (in real system, would use Gemini)
            if "burger" in text.lower():
                await self.search_menu("burger")
        
        elif event == "intent":
            intent = msg.payload.get("intent_type")
            print(f"\n💭 Intent: {intent}")
            print(f"   Entities: {msg.payload.get('entities', {})}")
            
            if intent == "search_menu":
                query = msg.payload.get("entities", {}).get("item", "")
                await self.search_menu(query)
    
    async def handle_input_event(self, msg: NATSMessage, subject: str):
        """Handle touch/input events from frontend."""
        action = msg.payload.get("action")
        
        if action == "select_item":
            item_id = msg.payload.get("item_id")
            print(f"\n👆 Touch: Selected item {item_id}")
            await self.get_item_details(item_id)
        
        elif action == "add_to_cart":
            item_id = msg.payload.get("item_id")
            print(f"\n🛒 Cart: Added item {item_id}")
    
    async def search_menu(self, query: str):
        """Send search request to Menu Agent and get suggestions."""
        print(f"\n🔍 Searching for: {query}")
        print("-" * 40)
        
        # Execute menu search and recsys suggest in parallel
        search_request = create_request(
            command="search",
            payload={"query": query, "limit": 5},
            session_id=self.session_id
        )
        
        suggest_request = create_request(
            command="suggest",
            payload={"cart": [], "context": {"weather": "hot"}},
            session_id=self.session_id
        )
        
        # Parallel execution
        try:
            menu_response, recsys_response = await asyncio.gather(
                self.client.request("kiosk.agent.menu.search", search_request),
                self.client.request("kiosk.agent.recsys.suggest", suggest_request),
                return_exceptions=True
            )
            
            # Process menu results
            if isinstance(menu_response, NATSMessage):
                items = menu_response.payload.get("items", [])
                print(f"\n📋 Menu Results ({len(items)} items):")
                for item in items:
                    print(f"   • {item['name']} - ${item['price']}")
            else:
                print(f"❌ Menu search failed: {menu_response}")
            
            # Process recommendations
            if isinstance(recsys_response, NATSMessage):
                suggestions = recsys_response.payload.get("suggestions", [])
                if suggestions:
                    print(f"\n💡 Suggestions:")
                    for s in suggestions:
                        print(f"   • {s['name']}: {s['pitch']}")
            else:
                print(f"❌ Recsys failed: {recsys_response}")
        
        except asyncio.TimeoutError:
            print("❌ Request timed out")
    
    async def get_item_details(self, item_id: int):
        """Get details for a specific item."""
        request = create_request(
            command="get_details",
            payload={"item_id": item_id},
            session_id=self.session_id
        )
        
        try:
            response = await self.client.request(
                "kiosk.agent.menu.details",
                request
            )
            
            if response.payload.get("status") == "success":
                item = response.payload.get("item", {})
                print(f"\n📄 Item Details:")
                print(f"   Name: {item.get('name')}")
                print(f"   Price: ${item.get('price')}")
                print(f"   Description: {item.get('description')}")
                print(f"   Calories: {item.get('calories')}")
            else:
                print(f"❌ Error: {response.payload.get('error_message')}")
        
        except asyncio.TimeoutError:
            print("❌ Request timed out")


async def main():
    orchestrator = MockOrchestrator()
    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        print("\n👋 Shutting down Orchestrator...")


if __name__ == "__main__":
    asyncio.run(main())
