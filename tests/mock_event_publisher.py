"""
Mock Event Publisher

Simulates Vision and Voice agents publishing events.
Use this to test the Orchestrator's event handling.
"""

import asyncio
import random

from common.client import KioskNATSClient, NATSConfig
from common.message import NATSMessage, create_event


class MockEventPublisher:
    """
    Simulates Vision and Voice agents publishing events.
    """
    
    def __init__(self):
        self.client = KioskNATSClient(
            config=NATSConfig(name="mock-event-publisher")
        )
        self.session_id = "test-session-001"
    
    async def connect(self):
        """Connect to NATS."""
        await self.client.connect()
    
    async def disconnect(self):
        """Disconnect from NATS."""
        await self.client.disconnect()
    
    # ========================================
    # Vision Events
    # ========================================
    
    async def publish_person_detected(self, party_size: int = 1):
        """Simulate a person being detected."""
        event = create_event(
            event_type="person_detected",
            payload={
                "confidence": random.uniform(0.85, 0.99),
                "face_detected": True,
                "estimated_age_group": random.choice(["child", "adult", "senior"]),
                "estimated_party_size": party_size,
                "bounding_box": {"x": 100, "y": 50, "w": 200, "h": 400}
            },
            session_id=self.session_id
        )
        await self.client.publish("kiosk.vision.person_detected", event)
    
    async def publish_person_left(self):
        """Simulate a person leaving."""
        event = create_event(
            event_type="person_left",
            payload={"duration_seconds": random.uniform(30, 120)},
            session_id=self.session_id
        )
        await self.client.publish("kiosk.vision.person_left", event)
    
    async def publish_gaze_detected(self, looking_at_screen: bool = True):
        """Simulate gaze detection."""
        event = create_event(
            event_type="gaze_detected",
            payload={
                "looking_at_screen": looking_at_screen,
                "gaze_point": {"x": random.randint(0, 1920), "y": random.randint(0, 1080)}
            },
            session_id=self.session_id
        )
        await self.client.publish("kiosk.vision.gaze_detected", event)
    
    # ========================================
    # Voice Events
    # ========================================
    
    async def publish_transcript(self, text: str):
        """Simulate a voice transcript."""
        event = create_event(
            event_type="transcript",
            payload={
                "text": text,
                "confidence": random.uniform(0.85, 0.99),
                "language": "en-US",
                "is_final": True
            },
            session_id=self.session_id
        )
        await self.client.publish("kiosk.voice.transcript", event)
    
    async def publish_intent(self, intent_type: str, entities: dict):
        """Simulate an intent being derived."""
        event = create_event(
            event_type="intent",
            payload={
                "intent_type": intent_type,
                "entities": entities,
                "confidence": random.uniform(0.80, 0.95)
            },
            session_id=self.session_id
        )
        await self.client.publish("kiosk.voice.intent", event)
    
    # ========================================
    # Input Events (Touch)
    # ========================================
    
    async def publish_touch_select(self, item_id: int):
        """Simulate a touch selection."""
        event = create_event(
            event_type="select_item",
            payload={
                "action": "select_item",
                "item_id": item_id,
                "component": "HeroItem"
            },
            session_id=self.session_id
        )
        await self.client.publish("kiosk.input.touch", event)
    
    async def publish_add_to_cart(self, item_id: int, quantity: int = 1):
        """Simulate adding item to cart."""
        event = create_event(
            event_type="cart_action",
            payload={
                "action": "add_to_cart",
                "item_id": item_id,
                "quantity": quantity
            },
            session_id=self.session_id
        )
        await self.client.publish("kiosk.input.cart_action", event)


async def interactive_publisher():
    """Interactive event publisher for manual testing."""
    publisher = MockEventPublisher()
    await publisher.connect()
    
    print("\n📡 Mock Event Publisher")
    print("=" * 50)
    print("Commands:")
    print("  1. Person detected")
    print("  2. Person left")
    print("  3. Voice: 'I want a burger'")
    print("  4. Voice: 'Show me vegetarian options'")
    print("  5. Touch: Select item 101")
    print("  6. Intent: search_menu(burger)")
    print("  q. Quit")
    print("=" * 50)
    
    try:
        while True:
            cmd = input("\nEnter command: ").strip().lower()
            
            if cmd == "1":
                await publisher.publish_person_detected(party_size=2)
            elif cmd == "2":
                await publisher.publish_person_left()
            elif cmd == "3":
                await publisher.publish_transcript("I want a burger")
            elif cmd == "4":
                await publisher.publish_transcript("Show me vegetarian options")
            elif cmd == "5":
                await publisher.publish_touch_select(item_id=101)
            elif cmd == "6":
                await publisher.publish_intent(
                    intent_type="search_menu",
                    entities={"item": "burger"}
                )
            elif cmd == "q":
                break
            else:
                print("Unknown command")
    
    finally:
        await publisher.disconnect()


async def main():
    await interactive_publisher()


if __name__ == "__main__":
    asyncio.run(main())
