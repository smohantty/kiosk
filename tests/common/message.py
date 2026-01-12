"""
NATS Message Envelope

Standardized message format for all kiosk components.
"""

import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class NATSMessage:
    """Standard message envelope for all NATS communication."""
    
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: str = ""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    payload: dict = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        payload: dict,
        session_id: str = "",
        trace_id: Optional[str] = None
    ) -> "NATSMessage":
        """Create a new message with auto-generated IDs."""
        return cls(
            session_id=session_id,
            trace_id=trace_id or str(uuid.uuid4()),
            payload=payload
        )
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        return json.dumps(asdict(self))
    
    def to_bytes(self) -> bytes:
        """Serialize message to bytes for NATS."""
        return self.to_json().encode('utf-8')
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "NATSMessage":
        """Deserialize message from NATS bytes."""
        obj = json.loads(data.decode('utf-8'))
        return cls(**obj)
    
    @classmethod
    def from_json(cls, json_str: str) -> "NATSMessage":
        """Deserialize message from JSON string."""
        obj = json.loads(json_str)
        return cls(**obj)


# ============================================================
# Event Payloads
# ============================================================

@dataclass
class PersonDetectedPayload:
    """Payload for vision.person_detected event."""
    event: str = "person_detected"
    confidence: float = 0.95
    face_detected: bool = True
    estimated_age_group: str = "adult"
    estimated_party_size: int = 1


@dataclass
class TranscriptPayload:
    """Payload for voice.transcript event."""
    event: str = "transcript"
    text: str = ""
    confidence: float = 0.90
    language: str = "en-US"
    is_final: bool = True


@dataclass
class IntentPayload:
    """Payload for voice.intent event."""
    event: str = "intent"
    intent_type: str = ""
    entities: dict = field(default_factory=dict)
    raw_text: str = ""
    confidence: float = 0.85


# ============================================================
# Command/Request Payloads
# ============================================================

@dataclass
class MenuSearchRequest:
    """Request payload for menu.search command."""
    command: str = "search"
    query: str = ""
    tags: list = field(default_factory=list)
    dietary_filters: list = field(default_factory=list)
    limit: int = 10


@dataclass
class MenuSearchResponse:
    """Response payload for menu.search command."""
    status: str = "success"
    items: list = field(default_factory=list)
    total_matches: int = 0


@dataclass
class RecsysSuggestRequest:
    """Request payload for recsys.suggest command."""
    command: str = "suggest"
    cart: list = field(default_factory=list)
    context: dict = field(default_factory=dict)


@dataclass
class RecsysSuggestResponse:
    """Response payload for recsys.suggest command."""
    status: str = "success"
    suggestions: list = field(default_factory=list)


# ============================================================
# Helper Functions
# ============================================================

def create_event(
    event_type: str,
    payload: dict,
    session_id: str = ""
) -> NATSMessage:
    """Create an event message."""
    return NATSMessage.create(
        payload={"event": event_type, **payload},
        session_id=session_id
    )


def create_request(
    command: str,
    payload: dict,
    session_id: str = ""
) -> NATSMessage:
    """Create a request message."""
    return NATSMessage.create(
        payload={"command": command, **payload},
        session_id=session_id
    )


def create_response(
    status: str,
    payload: dict,
    original_msg: NATSMessage
) -> NATSMessage:
    """Create a response message, preserving trace_id."""
    return NATSMessage.create(
        payload={"status": status, **payload},
        session_id=original_msg.session_id,
        trace_id=original_msg.trace_id
    )
