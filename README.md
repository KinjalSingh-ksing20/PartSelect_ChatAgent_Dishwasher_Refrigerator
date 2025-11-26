
# PartSelect AI Chat Agent

**Production-Grade AI Assistant for Appliance Parts**

A full-stack **AI-powered chat assistant** that helps users **search, troubleshoot, check compatibility, and install refrigerator & dishwasher parts** using:

* **FastAPI backend**
* **FAISS vector semantic search**
* **DeepSeek LLM**
* **React frontend**
* **Prometheus + Grafana observability**
* **OpenTelemetry tracing with Tempo**

This project is designed as a **real-world AI systems engineering case study** with full **guardrails, structured reasoning, deterministic tools, and production monitoring**.

---

## Key Features

| Capability                     | Description                                   |
| ------------------------------ | --------------------------------------------- |
| **Product Search**             | Semantic FAISS search over part catalog       |
| **Installation Guidance**      | LLM-generated steps using retrieved part data |
| **Compatibility Checks**       | Exact model/part verification                 |
| **Symptom Troubleshooting**    | Symptom-based part guidance                   |
| **Session Memory**             | Multi-turn conversation continuity            |
| **Hard Scope Guardrails**      | Only refrigerators & dishwashers allowed      |
| **Observability**              | Full metrics, traces, and dashboards          |
| **Safe LLM Usage**             | No hallucinated prices, models, or guarantees |

---

## System Architecture

```
User (Browser)
    |
    v
React Frontend (Vite)
    |
    v
FastAPI Backend
    |
    ├── Intent Classification
    ├── Entity Extraction
    ├── Session Memory
    |
    ├── FAISS Vector Search  ───► Part Catalog
    |
    ├── DeepSeek LLM
    |       └── Installation
    |       └── Troubleshooting
    |       └── Product Reasoning
    |
    ├── Prometheus Metrics  ───► Prometheus Server
    |
    └── OpenTelemetry Traces ───► Tempo ───► Grafana
```

---



## Repository Structure

```
backend/
  agents/           # Core agent reasoning
  data/             # Catalog, registries
  memory/           # Session memory
  models/           # LLM adapter
  observability/    # Tracing + metrics
  vectorstore/      # FAISS index + search
  app.py            # FastAPI entrypoint

frontend/
  components/       # Chat UI + Product cards
  App.jsx
  index.css

observability/
  docker-compose.yml
  prometheus.yml
  grafana/
```

---

## End-to-End Request Flow

1️User sends message from React UI
2️FastAPI receives request at `/chat`
3️Agent:

* Loads **session memory**
* Extracts **brand, model, symptom, part #**
* Applies **scope guardrails**
  4️Depending on intent:
* Runs **FAISS semantic search**
* Calls **DeepSeek LLM** if reasoning needed
  5️Returns:
* Answer
* Tool used
* Tool output (products)
  6️ Prometheus records:
* Latency
* Usage counts
* Errors
  7️ Grafana dashboards update live

---

## Observability Stack

### Metrics Tracked

| Metric                               | Purpose              |
| ------------------------------------ | -------------------- |
| `deepseek_calls_total`               | LLM usage            |
| `vector_search_total`                | FAISS search count   |
| `agent_tool_invocations_total{tool}` | Tool usage breakdown |
| `errors_total{type}`                 | Backend failures     |
| `request_latency_seconds`            | Full chat latency    |

---

## 📈 Grafana Panels

| Panel                | Purpose                |
| -------------------- | ---------------------- |
| Vector Search Rate   | FAISS load             |
| LLM Call Rate        | Model cost visibility  |
| Tool Invocation Rate | Agent behavior         |
| Error Rate           | Reliability            |
|  Chat Latency        | Performance monitoring |

Latency query:

```promql
rate(request_latency_seconds_sum[1m]) 
/
rate(request_latency_seconds_count[1m])
```

---

##  Safety & Guardrails

| Protection             | Method                             |
| ---------------------- | ---------------------------------- |
| Out-of-scope filtering | Appliance keyword enforcement      |
| No hallucinated models | Deterministic compatibility checks |
| No fake prices         | Catalog-only context               |
| No unsafe advice       | Installation warnings included     |

---

## 🖥️ Local Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Observability

```bash
cd observability
docker compose up -d
```

Access:

* Frontend → `http://localhost:5173`
* Backend → `http://localhost:8000`
* Prometheus → `http://localhost:9090`
* Grafana → `http://localhost:3000`

---

## Example Test Prompts

| Query                                  | Expected Behavior         |
| -------------------------------------- | ------------------------- |
| “My microwave isn’t working”           | ❌ Out-of-scope response   |
| “How do I install PS11752778?”         | ✅ Installation steps      |
| “Is this compatible with WDT780SAEM1?” | ✅ Compatibility check     |
| “My Whirlpool ice maker isn’t working” | ✅ Symptom-based guidance  |
| “My dishwasher isn’t working”          | ✅ General troubleshooting |

---

## Engineering Highlights

* Deterministic compatibility verification
* Agentic controller with tool routing
* Traceable AI pipelines
* Production-grade monitoring
* Fail-safe hallucination protection

---

##  Author

**Kinjal Singh**
University of Illinois Urbana-Champaign

---
