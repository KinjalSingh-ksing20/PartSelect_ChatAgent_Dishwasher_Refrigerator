# backend/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict

# --- Observability ---
from observability.tracing import setup_tracing
from prometheus_fastapi_instrumentator import Instrumentator

from agents.agent import AgentController


# ------------------------------------
# FastAPI App Config
# ------------------------------------
app = FastAPI(
    title="PartSelect Chat Agent",
    description="Backend for refrigerator/dishwasher Parts Chat Agent using DeepSeek + FAISS.",
    version="0.1.0",
)

# Initialize OpenTelemetry tracing
tracer = setup_tracing()

Instrumentator().instrument(app).expose(app)


# CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = AgentController()


# -------------------------
# Pydantic Models
# -------------------------
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    intent: str
    entities: Dict[str, Any]
    tool_used: str | None
    tool_output: Any
    answer: str


class CompatibilityRequest(BaseModel):
    part_number: str
    model_number: str


class InstallationRequest(BaseModel):
    part_number: str


class TroubleshootRequest(BaseModel):
    description: str


# -------------------------
# Routes
# -------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return await agent.handle_chat(req.message)


@app.post("/compatibility")
async def compatibility(req: CompatibilityRequest):
    return await agent.check_compatibility(req.part_number, req.model_number)


@app.post("/installation")
async def installation(req: InstallationRequest):
    return await agent.get_installation(req.part_number)


@app.post("/troubleshoot")
async def troubleshoot(req: TroubleshootRequest):
    return await agent.troubleshoot(req.description)

