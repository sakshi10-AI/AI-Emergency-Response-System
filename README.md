# 🚨 AI Emergency Response System (EOC Command Center)

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32-FF4B4B.svg)](https://streamlit.io/)
[![Google Gemini API](https://img.shields.io/badge/AI-Google%20Gemini%20API-4285F4.svg)](https://ai.google.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.2-DC382D.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Production%20Ready-2496ED.svg)](https://www.docker.com/)
[![Coverage](https://img.shields.io/badge/Coverage-%3E90%25-brightgreen.svg)](https://docs.pytest.org/)

An enterprise-grade, production-ready **AI Emergency Response System (ERS)** powered by a **Multi-Agent AI Architecture** utilizing the **Google Gemini API**, **LangGraph Workflow Engine**, **FastAPI**, **Streamlit Command Center UI**, **Redis Memory Store**, and **PostgreSQL/PostGIS Database**.

---

## 🏛️ System Architecture

The platform follows a decoupled, resilient microservices architecture separating presentation, API routing, multi-agent AI execution, state persistence, and real-time WebSocket streaming.

```mermaid
graph TD
    subgraph Presentation Layer ["💻 Presentation Layer (Streamlit Command Center)"]
        UI[Streamlit EOC Dashboard]
        WS_CLIENT[Resilient WebSocket & Polling Fallback Client]
        API_CLIENTS[Decoupled API Service Clients]
    end

    subgraph API Gateway Layer ["⚡ API Gateway & Security (FastAPI)"]
        AUTH[JWT & 5-Role RBAC Middleware]
        ROUTERS[FastAPI Domain Routers]
        WS_ROUTER[WebSocket Manager & Telemetry Stream]
    end

    subgraph AI Core Layer ["🧠 Multi-Agent AI Core (LangGraph & Gemini API)"]
        SUPERVISOR[Supervisor Agent]
        VISION[Computer Vision Hazard Agent]
        SEVERITY[Severity Triage Agent]
        HOSPITAL[Hospital Routing Agent]
        AMBULANCE[Ambulance Dispatch Agent]
        TRAFFIC[Traffic Signal Preemption Agent]
        REPORT[AI Report Synthesis Agent]
    end

    subgraph Persistence Layer ["💾 Persistent Storage & Telemetry Memory"]
        POSTGRES[(PostgreSQL / PostGIS Database)]
        REDIS[(Redis State & Checkpoint Store)]
    end

    UI --> API_CLIENTS
    UI --> WS_CLIENT
    API_CLIENTS --> AUTH
    WS_CLIENT --> WS_ROUTER
    AUTH --> ROUTERS
    ROUTERS --> SUPERVISOR
    SUPERVISOR --> VISION
    SUPERVISOR --> SEVERITY
    SUPERVISOR --> HOSPITAL
    SUPERVISOR --> AMBULANCE
    SUPERVISOR --> TRAFFIC
    SUPERVISOR --> REPORT
    ROUTERS --> POSTGRES
    SUPERVISOR --> REDIS
```

---

## 🔄 Multi-Agent Workflow Execution

The emergency dispatch lifecycle is managed autonomously via LangGraph state graphs with human-in-the-loop supervisor override controls:

```mermaid
sequenceDiagram
    autonumber
    actor Caller as Emergency Caller / Camera Stream
    participant Vision as Vision Hazard Agent
    participant Severity as Severity Triage Agent
    participant Hospital as Hospital Routing Agent
    participant Ambulance as Ambulance Dispatch Agent
    participant Traffic as Traffic Signal Agent
    participant DB as PostgreSQL & Redis Store

    Caller->>Vision: Upload Camera Feed / Incident Text
    Vision->>Severity: Detect Hazard Bounding Boxes & Confidence (96%)
    Severity->>Hospital: Assign Priority Level (Level 1 Critical)
    Hospital->>Ambulance: Select Optimal Hospital (SF General Level I)
    Ambulance->>Traffic: Dispatch Nearest Unit (AMB-101 ALS)
    Traffic->>DB: Preempt Signal Corridor & Commit Audit Logs
    DB-->>Caller: Real-Time Telemetry Stream & PDF Report Ready
```

---

## 📁 Complete Folder Structure

```
ai-emergency-response-system/
├── agents/                 # Multi-Agent AI Core (Supervisor, Vision, Severity, Hospital, Ambulance, Traffic, Report)
├── authentication/         # JWT Token Generation (Access & 7-Day Refresh Tokens) & RBAC Dependencies
├── backend/                # FastAPI Application Entrypoint, Lifespan Hooks, CORS & Middleware
├── config/                 # Pydantic BaseSettings Loading Environment Parameters
├── database/               # Async SQLAlchemy Engine, Base Declarative Metadata & DB Connection Pool
├── deployment/             # Multi-Stage Dockerfiles (Dockerfile.frontend), Nginx & Compose Configs
├── docs/                   # System Architecture Documentation & Technical Specifications
├── frontend/               # Streamlit EOC Presentation UI
│   ├── api_clients/        # Decoupled API Service Clients (Base, Auth, Incident, Hospital, Ambulance, Report, Notification)
│   ├── views/              # 10 Independent Page Views (Dashboard, Live Camera, Uploads, Details, Hospitals, Fleet, Analytics, Reports, Settings, Login)
│   ├── auth_guard.py       # Role Permission Matrix & Access Control Guards
│   ├── realtime_sync.py    # Thread-Safe Real-Time Event Sync to Session State
│   └── websocket_client.py # Resilient WebSocket Daemon with Reconnect Loop & HTTP Polling Fallback
├── memory/                 # Modular Redis Persistence (Workflow, Incident, Agent, Session, Task Queue, Checkpoints)
├── middleware/             # Request Exception Handling, CORS & Logging
├── models/                 # SQLAlchemy 2.0 ORM Entities (User, Incident, ResponderUnit, DispatchAssignment, PublicAlert, AgentAuditLog, IncidentReport)
├── routers/                # FastAPI Routers (Auth, Incidents, Units, Hospitals, Reports, Notifications, WebSockets, Health)
├── schemas/                # Pydantic DTO Validation Schemas
├── services/               # Business Logic Services (Incident Service, User Service, Report & PDF/CSV Export Service)
├── tests/                  # Automated Test Suite (>90% Code Coverage)
├── utils/                  # Loguru Logger, Gemini LLM API Wrapper, Custom Exceptions & Helpers
├── vision/                 # OpenCV / YOLOv11 Computer Vision Hazard Detector & Bounding Box Utilities
├── Dockerfile              # Multi-Stage Production Dockerfile for FastAPI Backend
├── docker-compose.yml      # 4-Microservice Container Orchestration (FastAPI, Streamlit, Redis, PostgreSQL)
├── requirements.txt        # Python Package Dependencies
└── README.md               # Project Master Documentation
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose**
- **Google Gemini API Key**

### 2. Local Environment Setup
Clone repository and create a Python virtual environment:
```bash
git clone https://github.com/organization/ai-emergency-response-system.git
cd ai-emergency-response-system

python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and configure credentials:
```bash
cp .env.example .env
```
Ensure your `.env` contains:
```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_password
POSTGRES_DB=ai_emergency_db
DATABASE_URL=postgresql+asyncpg://postgres:postgres_password@localhost:5432/ai_emergency_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=eoc-super-secret-jwt-signing-key-change-in-prod-2026!
GEMINI_API_KEY=your_google_gemini_api_key_here
```

---

## 🐳 Docker Production Deployment

Deploy the full 4-microservice container stack (**FastAPI Backend**, **Streamlit Dashboard**, **Redis Memory**, **PostgreSQL Database**) using Docker Compose:

```bash
docker-compose up --build -d
```

### Microservice Endpoints
- **Streamlit Command Center**: http://localhost:8501
- **FastAPI Backend API**: http://localhost:8000
- **Interactive OpenAPI (Swagger) Docs**: http://localhost:8000/docs
- **ReDoc Technical Specs**: http://localhost:8000/redoc
- **PostgreSQL Database**: `localhost:5432`
- **Redis Memory Store**: `localhost:6379`

To inspect service health and container status:
```bash
docker-compose ps
```

---

## 📖 API Documentation & Endpoints

### 🔐 Authentication & RBAC (`/api/v1/auth`)
- `POST /api/v1/auth/register` — Register new officer account.
- `POST /api/v1/auth/login` — Authenticate credentials & receive JWT access + refresh tokens.
- `POST /api/v1/auth/refresh` — Exchange refresh token for fresh access token.
- `GET /api/v1/auth/me` — Retrieve active profile.

### 🚨 Emergency Incidents (`/api/v1/incidents`)
- `POST /api/v1/incidents/` — Report new incident.
- `GET /api/v1/incidents/` — List incidents with filters.
- `GET /api/v1/incidents/{incident_id}` — Get detailed incident record.
- `PATCH /api/v1/incidents/{incident_id}/status` — Update incident status.
- `POST /api/v1/incidents/{incident_id}/approve` — Submit supervisor approval for dispatch.

### 🏥 Hospital Network (`/api/v1/hospitals`)
- `GET /api/v1/hospitals/` — Query regional trauma network.
- `POST /api/v1/hospitals/{hospital_id}/reserve-bed` — Reserve ICU bed.
- `PUT /api/v1/hospitals/{hospital_id}/capacity` — Update live capacity metrics.

### 🚑 Ambulance Fleet (`/api/v1/units`)
- `GET /api/v1/units/` — Query fleet units.
- `PUT /api/v1/units/{unit_id}/status` — Update unit status.
- `PUT /api/v1/units/{unit_id}/location` — Update GPS coordinates.

### 📑 Reports & Analytics (`/api/v1/reports`)
- `POST /api/v1/reports/` — Persist formal report in PostgreSQL DB.
- `GET /api/v1/reports/export/pdf` — Stream & download formal PDF report.
- `GET /api/v1/reports/export/csv` — Stream & download raw CSV dataset.
- `GET /api/v1/reports/analytics` — Retrieve 8 BI analytics datasets.

---

## 🖼️ Dashboard Interface Screenshots

| Operational View | Interface Preview | Description |
| :--- | :--- | :--- |
| **Command Center Dashboard** | `![Dashboard](docs/screenshots/dashboard.png)` | Real-time KPI metrics, interactive Folium map, and dispatch queue. |
| **Live Camera Feed** | `![Live Camera](docs/screenshots/live_camera.png)` | Real-time Computer Vision hazard detection and bounding box overlays. |
| **Hospital Matrix** | `![Hospital Dashboard](docs/screenshots/hospitals.png)` | ICU bed occupancy, ER load indicators, and one-click bed reservation. |
| **Ambulance Radar** | `![Ambulance Radar](docs/screenshots/ambulances.png)` | Real-time GPS unit tracking, fuel levels, and dispatch status controls. |
| **Executive BI Analytics** | `![Analytics](docs/screenshots/analytics.png)` | 8 interactive Plotly charts and PDF/CSV dashboard export bar. |
| **Post-Incident Reports** | `![Reports](docs/screenshots/reports.py)` | PostgreSQL report storage, officer notes, evidence gallery, and PDF/CSV downloads. |

---

## 🛠️ Developer Guide & Testing

### Running Tests
Execute full test suite with coverage reporting:
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

### Test Categories
- **Unit Tests**: `tests/test_agents.py`, `tests/test_gemini_wrapper.py`
- **API Tests**: `tests/test_api_endpoints.py`, `tests/test_api_clients.py`
- **Database Tests**: `tests/test_database_persistence.py`
- **Workflow Tests**: `tests/test_langgraph_workflow.py`
- **Vision Tests**: `tests/test_vision_module.py`
- **Authentication & RBAC Tests**: `tests/test_authentication_rbac.py`
- **System Integration Tests**: `tests/test_system_integration.py`
- **Docker Tests**: `tests/test_docker_deployment.py`

---

## ❓ Troubleshooting Guide

| Issue | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Redis Connection Error** | Redis container not running | Ensure `docker-compose up -d redis` is running or set local `REDIS_HOST=localhost`. System falls back to in-memory store. |
| **PostgreSQL Connection Error** | Database credentials mismatch | Check `.env` parameters (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`). Run `docker-compose logs database`. |
| **Gemini API Rate Limit** | Invalid or missing API Key | Set a valid `GEMINI_API_KEY` in `.env`. System operates in heuristic fallback mode when key is absent. |
| **WebSocket Connection Dropped** | Port 8000 unreachable | Client automatically activates **HTTP Polling Fallback Mode** with zero Streamlit UI crashes. |

---

## 🚀 Future Scope

- **Autonomous Drone Dispatch**: Integration of aerial reconnaissance drones for immediate visual triage.
- **Edge AI Video Processing**: Deployment of lightweight YOLO models directly on smart traffic light hardware.
- **Nationwide EOC Interconnectivity**: Cross-regional federated multi-agency dispatch network.
- **Predictive Disaster Modeling**: Machine learning forecasting for natural disaster resource allocation.

---

## 🤝 Contribution & License

Contributions are welcome! Please submit Pull Requests following our branching convention (`feature/` or `fix/`).

Distributed under the **MIT License**. See `LICENSE` for details.
