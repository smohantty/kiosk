# Tech Stack Selection & Justification

## 1. Hardware Platform: NVIDIA Jetson Orin Nano
*   **Why**: Specific user requirement and best-in-class entry-level Edge AI.
*   **Specs**: 6-core ARM CPU, Ampere GPU (1024 CUDA cores), 8GB RAM.
*   **Role**:
    *   Runs the Local Orchestrator (Privacy & Latency).
    *   Runs Real-time Computer Vision (Face tracking, Gaze).
    *   Runs Local STT (Speech-to-Text) / TTS to reduce cloud latency.
    *   Hosts the Web Kiosk (via HDMI/DP).

## 2. Intelligence Layer: Google Gemini (LLM)
*   **Why**: Specific user requirement.
*   **Integration**: `google-generativeai` SDK.
*   **Role**:
    *   **Complex Reasoning**: Understanding "I want something healthy but spicy".
    *   **Multi-Modal Analysis**: If camera frames are sent to cloud, Gemini 1.5 Pro can analyze user emotion/demographics directly.
    *   **Orchestration Logic**: Deciding which agent should handle a query.
    *   **UI Generation**: outputting structured JSON that the frontend renders.

## 3. Orchestration & Backend: Python + FastAPI
*   **Why Python**: The native language of AI. Essential for utilizing Jetson libraries (CUDA, TensorRT) and Gemini SDK seamlessly.
*   **Why FastAPI**:
    *   Asynchronous (Critical for handling multiple agents).
    *   **LiveKit Integration**: Simplifies WebRTC handling for Voice/Video via `livekit-agents` (Python SDK).
    *   Type safety with Pydantic (great for LLM structured outputs).

## 4. Multi-Agent Framework: LangGraph
*   **Why**:
    *   Provides fine-grained control over Agent flows (Cyclic graphs allowed).
    *   State management (checkpoints) is built-in.
    *   Much more deterministic than autonomous loops (Crucial for a payment/business context).

## 5. Generative UI Frontend: Next.js (React) + Tailwind CSS
*   **Why Next.js**:
    *   Industry standard for responsive, high-performance web apps.
    *   Capabilities for SSR (Server Side Rendering) if needed, though mostly Client-Side for this kiosk.
*   **Tailwind CSS**:
    *   Rapid styling.
    *   Easy for the LLM to "hallucinate" valid styles if it generates UI code or classes directly.
*   **Communication**: 
    *   **LiveKit Client**: Handles real-time Audio (Mic/Speaker) and Video (Camera).
    *   **Socket.IO**: Retained for low-frequency events (e.g., "Add to cart" clicks) if not using LiveKit Data Channels.

## 6. Edge AI Services (Local on Orin)
To minimize latency and cost, not everything goes to Gemini.
*   **Speech-to-Text (STT)**: **Faster-Whisper** (running on GPU).
    *   *Justification*: Waiting for cloud transcription for every "Select this" command is too slow. Local Whisper is near-instant.
    *   *Role*: Provide STT/TTS models exposed via plugins to LiveKit or local API.
*   **Computer Vision**: **DeepStream** (Pipeline) or **LiveKit Vision Plugin**.
    *   *Role*: Analyze the video stream frame-by-frame. LiveKit allows tapping into the video track on the backend side easily.

## 7. Database/Storage
*   **Redis**: For ephemeral session state (Cart, User Context).
*   **SQLite/PostgreSQL**: For Menu catalog and Transaction logs.

## 8. Alternatives Analysis (Re-evaluation: Adopting LiveKit)

### 8.1 Why LiveKit Locally?
Initial design excluded LiveKit to avoid overhead. However, upon re-evaluation, running **LiveKit Server** locally (via Docker) on the Orin Nano provides significant architectural benefits that outweigh the resource cost:
*   **Unified Multimodal Pipeline**: `livekit-agents` framework (Python) standardizes how we handle user voice and video. We don't need to write custom WebSocket chunkers for audio.
*   **Frontend Simplicity**: The Next.js app just uses the standard `livekit-client-sdk`.
*   **Remote Ready**: If we *do* need to debug a kiosk remotely, we can simple "join" the room from a laptop.
*   **Implementation**:
    *   **LiveKit Server**: Runs in Docker on Jetson.
    *   **Egress**: Local Loopback.
    *   **Latency**: Negligible (Localhost WebRTC).

