# Component Design & Specifications

This document details the internal design of each component and how they interact.

---

## 1. Orchestrator (The "Brain")

The Orchestrator is a stateful agent that manages the interaction loop. It coordinates other agents via **NATS** messages and controls the Generative UI.

### 1.1 Responsibilities

| Responsibility | Description |
|----------------|-------------|
| State Management | Tracks session state (cart, preferences, history) |
| Intent Routing | Dispatches processed intents to appropriate agents |
| UI Generation | Produces UI State JSON for the frontend |
| Response Synthesis | Combines agent outputs into coherent responses |
| Error Handling | Implements fallback strategies when agents fail |

### 1.2 State Machine

The Orchestrator transitions through these states:

```mermaid
stateDiagram-v2
    [*] --> IDLE
    
    IDLE --> ATTRACT: vision.person_detected
    ATTRACT --> LISTENING: user.engaged
    
    LISTENING --> PROCESSING: voice.detected
    LISTENING --> IDLE: timeout(30s)
    
    PROCESSING --> DECIDING: intent.derived
    PROCESSING --> LISTENING: intent.unclear
    
    DECIDING --> UPDATING: response.ready
    
    UPDATING --> LISTENING: continue
    UPDATING --> CHECKOUT: payment.requested
    
    CHECKOUT --> IDLE: transaction.complete
    CHECKOUT --> UPDATING: payment.failed
```

### 1.3 State Definitions

| State | Description | Entry Trigger | Exit Actions |
|-------|-------------|---------------|--------------|
| `IDLE` | Kiosk dormant, low power | Boot or session end | Clear session state |
| `ATTRACT` | Welcoming animation | Person detected | Start VAD listening |
| `LISTENING` | Waiting for user input | User engagement | Monitor audio/touch |
| `PROCESSING` | STT + Intent analysis | Voice detected | Call Gemini for intent |
| `DECIDING` | Routing to sub-agents | Intent derived | Dispatch NATS requests |
| `UPDATING` | Generating UI response | Agent replies received | Emit UI JSON + TTS |
| `CHECKOUT` | Payment flow active | User confirms cart | Hand off to PaymentAgent |

### 1.4 Session Context

The Orchestrator maintains a `SessionContext` object in Redis:

```json
{
  "session_id": "uuid-v4",
  "state": "LISTENING",
  "started_at": "2026-01-12T08:30:00Z",
  "user_demographics": {
    "age_group": "adult",
    "emotion": "happy",
    "party_size": 2
  },
  "cart": [
    {"item_id": 101, "name": "Volcano Burger", "qty": 1, "price": 12.99}
  ],
  "dietary_restrictions": ["vegetarian"],
  "interaction_history": [
    {"type": "showed", "items": ["burgers"]},
    {"type": "rejected", "items": ["fries"]}
  ],
  "last_activity": "2026-01-12T08:32:00Z"
}
```

---

## 2. Agent Definitions

### 2.1 Overview Diagram

```mermaid
graph TD
    Orch[Orchestrator]
    
    subgraph "Perception Agents"
        Vision[Vision Agent]
        Voice[Voice Agent]
    end
    
    subgraph "Domain Agents"
        Menu[Menu Agent]
        Rec[Recommendation Agent]
        Pay[Payment Agent]
    end
    
    subgraph "Hardware Agents"
        HW[Hardware Liaison]
    end
    
    Vision -->|person.detected| Orch
    Voice -->|intent.derived| Orch
    
    Orch <-->|search/response| Menu
    Orch <-->|suggest/response| Rec
    Orch <-->|process/response| Pay
    Orch -->|command| HW
```

### 2.2 Vision Agent

| Aspect | Details |
|--------|---------|
| **Role** | Detect and track users via camera |
| **Input** | Video stream from DeepStream |
| **Output** | Events: `person.detected`, `person.left`, `gaze.at_screen` |
| **Technology** | DeepStream + TensorRT models |

#### ✅ Does
- Face detection and tracking
- Estimate number of people
- Detect when user is looking at screen
- Wake kiosk from IDLE state

#### ❌ Doesn't
- Identify specific individuals (no facial recognition storage)
- Process audio
- Make menu decisions

---

### 2.3 Voice Agent

| Aspect | Details |
|--------|---------|
| **Role** | Convert speech to text and derive intent |
| **Input** | Audio stream from LiveKit |
| **Output** | Events: `text.transcribed`, `intent.derived` |
| **Technology** | NVIDIA Riva (STT) + Gemini (Intent) |

#### ✅ Does
- Voice activity detection (VAD)
- Streaming speech-to-text
- Intent classification via Gemini
- Language detection

#### ❌ Doesn't
- Process video
- Generate UI directly
- Handle payments

---

### 2.4 Menu Agent

| Aspect | Details |
|--------|---------|
| **Role** | RAG over menu database |
| **Input** | NATS: `agent.menu.search`, `agent.menu.details` |
| **Output** | Menu items matching query |
| **Technology** | SQLite + optional vector embeddings |

#### Tools

```python
class MenuAgent:
    def search_items(self, query: str, tags: list[str]) -> list[MenuItem]:
        """Search menu by text query and/or dietary tags."""
        
    def get_item_details(self, item_id: int) -> MenuItemDetails:
        """Get full details including nutrition, allergens."""
        
    def check_availability(self, item_id: int) -> bool:
        """Check real-time inventory status."""
```

#### ✅ Does
- Full-text search on menu items
- Filter by dietary restrictions
- Return nutritional information
- Check stock availability

#### ❌ Doesn't
- Make recommendations (that's RecsysAgent)
- Process payments
- Track user preferences

---

### 2.5 Recommendation Agent (RecsyS)

| Aspect | Details |
|--------|---------|
| **Role** | Proactive upselling and personalization |
| **Input** | NATS: `agent.recsys.suggest` with cart context |
| **Output** | Suggested items with pitch text |
| **Technology** | Rule-based + optional ML model |

#### Logic Flow

```mermaid
flowchart TD
    Input[Current Cart + Context]
    
    Rules{Rule Engine}
    Rules -->|Cart has burger| SuggestDrink[Suggest Cola]
    Rules -->|Time is afternoon| SuggestCoffee[Suggest Coffee]
    Rules -->|Weather is hot| SuggestCold[Suggest Ice Cream]
    Rules -->|Party has kids| SuggestKids[Suggest Kids Meal]
    
    Output[Top 1-3 Suggestions]
    
    Input --> Rules
    SuggestDrink --> Output
    SuggestCoffee --> Output
    SuggestCold --> Output
    SuggestKids --> Output
```

#### ✅ Does
- Context-aware suggestions
- Time/weather-based recommendations
- Combo/bundle detection
- Upsell pitch text generation

#### ❌ Doesn't
- Search menu (calls MenuAgent if needed)
- Store individual user profiles
- Process payments

---

### 2.6 Payment Agent

| Aspect | Details |
|--------|---------|
| **Role** | Secure transaction processing |
| **Input** | NATS: `agent.payment.process` |
| **Output** | Transaction result |
| **Technology** | Payment gateway SDK |

> [!CAUTION]
> This agent runs in an **isolated security zone**. All messages are encrypted.

#### ✅ Does
- Process card payments
- Handle loyalty points
- Generate transaction receipts
- Retry failed transactions

#### ❌ Doesn't
- Store card numbers (PCI-DSS)
- Log sensitive data
- Communicate over unencrypted channels

---

### 2.7 Hardware Liaison Agent

| Aspect | Details |
|--------|---------|
| **Role** | Control physical peripherals |
| **Input** | NATS: `agent.hardware.*` commands |
| **Output** | Confirmation events |
| **Technology** | Jetson GPIO + USB drivers |

#### Tools

```python
class HardwareLiaisonAgent:
    def set_led_strip(self, color: str, pattern: str):
        """Control LED strip: 'pulse', 'solid', 'error'."""
        
    def print_receipt(self, receipt_data: ReceiptData):
        """Send receipt to thermal printer."""
        
    def dispense_card(self):
        """Trigger card dispenser (if applicable)."""
```

---

## 3. Agent Communication Protocol

### 3.1 NATS Subject Naming

```
kiosk.{domain}.{action}

Examples:
- kiosk.vision.person_detected    (Pub/Sub event)
- kiosk.agent.menu.search         (Request/Reply)
- kiosk.agent.payment.process     (Request/Reply)
- kiosk.ui.update                 (Pub/Sub to frontend)
```

### 3.2 Communication Patterns

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant N as NATS
    participant M as MenuAgent
    participant R as RecsysAgent
    
    Note over O,R: Request-Reply (Synchronous)
    O->>N: Request: kiosk.agent.menu.search<br/>{"query": "burger"}
    N->>M: Deliver
    M-->>N: Reply: [items]
    N-->>O: Deliver Reply
    
    Note over O,R: Parallel Requests
    par Fetch Menu
        O->>N: Request: agent.menu.search
    and Fetch Suggestions
        O->>N: Request: agent.recsys.suggest
    end
    N-->>O: Menu items
    N-->>O: Suggestions
    
    Note over O,R: Pub/Sub (Async Events)
    O->>N: Publish: kiosk.cart.updated
    N->>R: Deliver to Subscriber
    R->>N: Publish: kiosk.suggestion.ready
    N->>O: Deliver
```

### 3.3 Message Envelope

All NATS messages use this envelope:

```json
{
  "msg_id": "uuid",
  "timestamp": "2026-01-12T08:30:00Z",
  "session_id": "session-uuid",
  "payload": { ... },
  "trace_id": "trace-uuid"
}
```

---

## 4. Generative UI Protocol (UI-over-JSON)

The Orchestrator doesn't send HTML. It sends a **UI Descriptor**. The Next.js frontend is a "dumb" renderer.

### 4.1 Schema Definition

```json
{
  "layout_mode": "hero_grid",
  "theme_override": "spicy_season",
  "auditory_response": "Here are our spicy options.",
  "components": [
    {
      "type": "HeroItem",
      "data": {
        "id": 101,
        "image": "/img/burger.png",
        "title": "Volcano Burger",
        "badge": "🔥 Hot"
      }
    },
    {
      "type": "Carousel",
      "items": ["..."]
    },
    {
      "type": "CartSummary",
      "data": {
        "item_count": 2,
        "total": 24.99
      }
    }
  ],
  "suggested_actions": [
    {"label": "Add to cart", "action": "add_item", "item_id": 101},
    {"label": "Show less spicy", "action": "filter", "tag": "mild"}
  ]
}
```

### 4.2 Component Types

| Component | Purpose |
|-----------|---------|
| `HeroItem` | Large featured item |
| `Carousel` | Horizontal scrollable list |
| `Grid` | Multi-column item display |
| `CartSummary` | Floating cart indicator |
| `Modal` | Overlay for confirmations |
| `Notification` | Toast-style alerts |

### 4.3 Feedback Loop

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant O as Orchestrator
    participant M as MenuAgent
    participant R as RecsysAgent
    
    U->>F: Touches "Volcano Burger"
    F->>O: LiveKit Data: {action: "select_item", id: 101}
    O->>O: Update cart in Redis
    
    par Get Details
        O->>M: Get item details
    and Get Upsell
        O->>R: Get suggestion
    end
    
    M-->>O: Item details
    R-->>O: "Add a drink?"
    
    O->>F: UI JSON: Item detail modal + Add Drink suggestion
    O->>F: TTS: "Great choice! Would you like a drink?"
    F->>U: Renders UI + Plays audio
```

---

## 5. Deployment Architecture

### 5.1 Resource Allocation

```mermaid
graph TB
    subgraph "Jetson Orin Nano (8GB Unified RAM)"
        subgraph "Docker Services (~300MB)"
            D1[LiveKit Server<br/>~200MB]
            D2[NATS JetStream<br/>~50MB]
            D3[Redis<br/>~50MB]
        end
        
        subgraph "Native Processes (~2GB)"
            P1[DeepStream Pipeline<br/>~1GB GPU/RAM]
            P2[Orchestrator + Agents<br/>~500MB RAM]
            P3[NVIDIA Riva<br/>~500MB GPU/RAM]
        end
        
        subgraph "Browser (~500MB)"
            B1[Chromium Kiosk Mode]
        end
        
        subgraph "Headroom (~5GB)"
            H1[Available for peaks]
        end
    end
    
    style D1 fill:#4a9eff
    style D2 fill:#4a9eff
    style D3 fill:#4a9eff
    style P1 fill:#ff6b6b
    style P2 fill:#ff6b6b
    style P3 fill:#ff6b6b
    style B1 fill:#51cf66
    style H1 fill:#d3d3d3
```

### 5.2 Docker Compose Structure

```yaml
# docker-compose.yml
services:
  livekit:
    image: livekit/livekit-server:latest
    ports: ["7880:7880", "7881:7881", "7882:7882/udp"]
    
  nats:
    image: nats:latest
    command: ["-js"]
    ports: ["4222:4222"]
    
  redis:
    image: redis:alpine
    ports: ["6379:6379"]
    volumes: ["redis-data:/data"]
```

---

## 6. Sequence Diagram: Complete Ordering Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend as Frontend (Next.js)
    participant Orch as Orchestrator
    participant Voice as VoiceAgent
    participant Menu as MenuAgent
    participant Rec as RecsysAgent
    participant Pay as PaymentAgent
    participant HW as HardwareAgent

    Note over User,HW: 1. Attract Phase
    User->>Frontend: Approaches kiosk
    Frontend->>Orch: vision.person_detected
    Orch->>Frontend: UI: Welcome animation
    Orch->>HW: LED: pulse blue
    
    Note over User,HW: 2. Order Phase
    User->>Frontend: "I want a burger"
    Frontend->>Voice: Audio stream
    Voice->>Orch: intent: {action: "search", query: "burger"}
    
    par Parallel Agent Calls
        Orch->>Menu: search("burger")
        Orch->>Rec: suggest(cart=[])
    end
    
    Menu-->>Orch: [Volcano Burger, Classic Burger, ...]
    Rec-->>Orch: Suggestion: "Add fries?"
    
    Orch->>Frontend: UI: Burger grid + Fries sidebar
    Orch->>Frontend: TTS: "Here are our burgers!"
    
    Note over User,HW: 3. Selection Phase
    User->>Frontend: Taps Volcano Burger
    Frontend->>Orch: action: {select: 101}
    Orch->>Orch: Add to cart
    Orch->>Frontend: UI: Updated cart
    
    Note over User,HW: 4. Checkout Phase
    User->>Frontend: "I'm ready to pay"
    Frontend->>Voice: Audio
    Voice->>Orch: intent: {action: "checkout"}
    
    Orch->>Pay: process(cart, total: 12.99)
    Pay->>User: Card reader prompt
    User->>Pay: Taps card
    Pay-->>Orch: {status: "success", txn_id: "..."}
    
    Orch->>HW: print_receipt(order)
    Orch->>Frontend: UI: "Thank you!" screen
    Orch->>HW: LED: solid green (2s)
    
    Note over User,HW: 5. Reset
    Orch->>Orch: Clear session
    Orch->>Frontend: UI: Return to IDLE
```
