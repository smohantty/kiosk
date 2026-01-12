# NATS Test Infrastructure

This directory contains test clients and examples for NATS-based component communication.

## Quick Start

```bash
# 1. Start NATS server
docker-compose up -d nats

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the integration test
python -m tests.integration_test

# 4. Run individual mock agents
python -m tests.mock_menu_agent
python -m tests.mock_orchestrator
```

## Directory Structure

```
tests/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── common/
│   ├── __init__.py
│   ├── message.py       # Message envelope
│   └── client.py        # Base NATS client
├── mock_menu_agent.py   # Menu agent simulator
├── mock_recsys_agent.py # Recommendation agent simulator
├── mock_orchestrator.py # Orchestrator simulator
└── integration_test.py  # Full flow test
```

## Test Scenarios

1. **Pub/Sub Events**: Vision/Voice agents publish events, Orchestrator subscribes
2. **Request/Reply**: Orchestrator sends commands to agents, receives responses
3. **Parallel Requests**: Orchestrator queries multiple agents simultaneously

## Message Flow Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Vision Agent   │────▶│      NATS        │◀────│  Menu Agent     │
│  (Publisher)    │     │                  │     │  (Responder)    │
└─────────────────┘     │   JetStream      │     └─────────────────┘
                        │                  │
┌─────────────────┐     │  ┌───────────┐   │     ┌─────────────────┐
│  Voice Agent    │────▶│  │  Events   │   │◀────│  Recsys Agent   │
│  (Publisher)    │     │  │  Stream   │   │     │  (Responder)    │
└─────────────────┘     │  └───────────────┘     └─────────────────┘
                        │                  │
┌─────────────────┐     │  ┌───────────────┐     ┌─────────────────┐
│  Orchestrator   │◀───▶│  │  Commands │   │◀────│ Payment Agent   │
│  (Sub + Req)    │     │  │  Stream   │   │     │  (Responder)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```
