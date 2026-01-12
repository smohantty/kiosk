"""
Mock Recommendation Agent

Simulates the Recommendation Agent for testing NATS communication.
Provides upsell suggestions based on cart contents.
"""

import asyncio
import random

from common.client import KioskNATSClient, NATSConfig
from common.message import NATSMessage, create_response


# Suggestion rules
SUGGESTIONS = {
    "burger_combo": {
        "trigger": ["burger"],
        "item_id": 201,
        "name": "Crispy Fries",
        "pitch": "Make it a combo and save $2!",
        "reason": "upsell_combo"
    },
    "drink_suggestion": {
        "trigger": ["burger", "fries"],
        "item_id": 301,
        "name": "Iced Cola",
        "pitch": "Add a refreshing drink?",
        "reason": "complement"
    },
    "hot_weather": {
        "trigger": [],
        "context": {"weather": "hot"},
        "item_id": 301,
        "name": "Iced Cola",
        "pitch": "Perfect to cool down!",
        "reason": "weather_hot"
    }
}


class MockRecsysAgent:
    """Mock Recommendation Agent that suggests upsells."""
    
    def __init__(self):
        self.client = KioskNATSClient(
            config=NATSConfig(name="mock-recsys-agent")
        )
    
    async def start(self):
        """Start the mock agent."""
        await self.client.connect()
        
        # Register handler for suggestions
        await self.client.reply_handler(
            "kiosk.agent.recsys.suggest",
            self.handle_suggest,
            queue="recsys-agents"
        )
        
        print("\n💡 Mock Recommendation Agent ready!\n")
        await self.client.run_forever()
    
    async def handle_suggest(self, request: NATSMessage) -> NATSMessage:
        """Handle suggestion requests."""
        cart = request.payload.get("cart", [])
        context = request.payload.get("context", {})
        
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        suggestions = []
        cart_item_names = [item.get("name", "").lower() for item in cart]
        cart_item_ids = [item.get("item_id") for item in cart]
        
        # Check each suggestion rule
        for key, rule in SUGGESTIONS.items():
            # Skip if already in cart
            if rule["item_id"] in cart_item_ids:
                continue
            
            # Check trigger items
            trigger_match = any(
                trigger in name 
                for trigger in rule.get("trigger", [])
                for name in cart_item_names
            )
            
            # Check context match
            context_rule = rule.get("context", {})
            context_match = all(
                context.get(k) == v 
                for k, v in context_rule.items()
            )
            
            if trigger_match or (context_rule and context_match):
                suggestions.append({
                    "item_id": rule["item_id"],
                    "name": rule["name"],
                    "pitch": rule["pitch"],
                    "reason": rule["reason"]
                })
        
        # Limit to top 3 suggestions
        suggestions = suggestions[:3]
        
        return create_response(
            status="success",
            payload={"suggestions": suggestions},
            original_msg=request
        )


async def main():
    agent = MockRecsysAgent()
    try:
        await agent.start()
    except KeyboardInterrupt:
        print("\n👋 Shutting down Recsys Agent...")


if __name__ == "__main__":
    asyncio.run(main())
