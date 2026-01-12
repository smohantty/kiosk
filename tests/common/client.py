"""
Base NATS Client

Provides common functionality for all kiosk components to interact with NATS.
"""

import asyncio
import json
from typing import Callable, Optional, Any
from dataclasses import dataclass

import nats
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg
from nats.js import JetStreamContext

from .message import NATSMessage, create_response


@dataclass
class NATSConfig:
    """NATS connection configuration."""
    url: str = "nats://localhost:4222"
    name: str = "kiosk-client"
    reconnect_time_wait: int = 2
    max_reconnect_attempts: int = -1  # Infinite


class KioskNATSClient:
    """
    Base NATS client for kiosk components.
    
    Provides:
    - Connection management
    - Pub/Sub pattern
    - Request/Reply pattern
    - JetStream integration
    """
    
    def __init__(self, config: NATSConfig = None, name: str = "client"):
        self.config = config or NATSConfig(name=name)
        self.nc: Optional[NATSClient] = None
        self.js: Optional[JetStreamContext] = None
        self._subscriptions = []
        self._running = False
    
    async def connect(self) -> None:
        """Connect to NATS server."""
        self.nc = await nats.connect(
            servers=[self.config.url],
            name=self.config.name,
            reconnect_time_wait=self.config.reconnect_time_wait,
            max_reconnect_attempts=self.config.max_reconnect_attempts,
            error_cb=self._on_error,
            disconnected_cb=self._on_disconnect,
            reconnected_cb=self._on_reconnect,
        )
        
        # Initialize JetStream
        self.js = self.nc.jetstream()
        
        print(f"✅ Connected to NATS: {self.config.url} as '{self.config.name}'")
    
    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self.nc:
            await self.nc.drain()
            await self.nc.close()
            print(f"👋 Disconnected from NATS")
    
    # ========================================
    # Pub/Sub Pattern
    # ========================================
    
    async def publish(self, subject: str, message: NATSMessage) -> None:
        """
        Publish an event to a subject.
        
        Args:
            subject: NATS subject (e.g., "kiosk.vision.person_detected")
            message: NATSMessage to publish
        """
        await self.nc.publish(subject, message.to_bytes())
        print(f"📤 Published to {subject}: {message.payload.get('event', message.payload.get('command', 'message'))}")
    
    async def subscribe(
        self,
        subject: str,
        handler: Callable[[NATSMessage], Any],
        queue: str = None
    ) -> None:
        """
        Subscribe to a subject pattern.
        
        Args:
            subject: NATS subject pattern (e.g., "kiosk.vision.>")
            handler: Async function to handle received messages
            queue: Optional queue group for load balancing
        """
        async def _wrapper(msg: Msg):
            try:
                nats_msg = NATSMessage.from_bytes(msg.data)
                await handler(nats_msg, msg.subject)
            except Exception as e:
                print(f"❌ Error handling message on {msg.subject}: {e}")
        
        sub = await self.nc.subscribe(subject, queue=queue, cb=_wrapper)
        self._subscriptions.append(sub)
        print(f"📥 Subscribed to {subject}" + (f" (queue: {queue})" if queue else ""))
    
    # ========================================
    # Request/Reply Pattern
    # ========================================
    
    async def request(
        self,
        subject: str,
        message: NATSMessage,
        timeout: float = 5.0
    ) -> NATSMessage:
        """
        Send a request and wait for reply.
        
        Args:
            subject: NATS subject (e.g., "kiosk.agent.menu.search")
            message: Request message
            timeout: Timeout in seconds
            
        Returns:
            Response message from the agent
        """
        print(f"🔄 Request to {subject}: {message.payload.get('command', 'request')}")
        
        response = await self.nc.request(
            subject,
            message.to_bytes(),
            timeout=timeout
        )
        
        response_msg = NATSMessage.from_bytes(response.data)
        print(f"✅ Reply from {subject}: {response_msg.payload.get('status', 'received')}")
        
        return response_msg
    
    async def reply_handler(
        self,
        subject: str,
        handler: Callable[[NATSMessage], NATSMessage],
        queue: str = None
    ) -> None:
        """
        Set up a reply handler for request/reply pattern.
        
        Args:
            subject: NATS subject to listen on
            handler: Function that takes request and returns response
            queue: Optional queue group for load balancing
        """
        async def _wrapper(msg: Msg):
            try:
                request_msg = NATSMessage.from_bytes(msg.data)
                print(f"📨 Request received on {msg.subject}: {request_msg.payload.get('command', 'request')}")
                
                # Call handler to get response
                response_msg = await handler(request_msg)
                
                # Send reply
                await msg.respond(response_msg.to_bytes())
                print(f"📬 Reply sent: {response_msg.payload.get('status', 'response')}")
                
            except Exception as e:
                # Send error response
                error_response = create_response(
                    status="error",
                    payload={"error_code": "HANDLER_ERROR", "error_message": str(e)},
                    original_msg=NATSMessage.from_bytes(msg.data)
                )
                await msg.respond(error_response.to_bytes())
                print(f"❌ Error handling request: {e}")
        
        sub = await self.nc.subscribe(subject, queue=queue, cb=_wrapper)
        self._subscriptions.append(sub)
        print(f"🎯 Reply handler registered for {subject}" + (f" (queue: {queue})" if queue else ""))
    
    # ========================================
    # JetStream (Persistent Messages)
    # ========================================
    
    async def ensure_stream(self, name: str, subjects: list[str]) -> None:
        """Ensure a JetStream stream exists."""
        try:
            await self.js.add_stream(name=name, subjects=subjects)
            print(f"📚 Created stream: {name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"📚 Stream exists: {name}")
            else:
                raise
    
    # ========================================
    # Callbacks
    # ========================================
    
    async def _on_error(self, e):
        print(f"❌ NATS Error: {e}")
    
    async def _on_disconnect(self):
        print("⚠️ Disconnected from NATS")
    
    async def _on_reconnect(self):
        print("🔄 Reconnected to NATS")
    
    # ========================================
    # Run Loop
    # ========================================
    
    async def run_forever(self):
        """Keep the client running until interrupted."""
        self._running = True
        print("🚀 Client running. Press Ctrl+C to stop.")
        
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.disconnect()
    
    def stop(self):
        """Signal the client to stop."""
        self._running = False
