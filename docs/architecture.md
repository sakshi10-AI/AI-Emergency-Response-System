# Technical System Architecture & Multi-Agent Specifications

This document outlines the detailed system architecture, multi-agent workflow state machine, data models, and component interactions of the **AI Emergency Response System (EOC Command Center)**.

---

## 1. High-Level Microservice Topology

The application is structured into 4 decoupled microservice containers managed by Docker Compose:

```mermaid
graph LR
    subgraph Client ["Client Browser"]
        ST[Streamlit Dashboard :8501]
    end

    subgraph Service ["FastAPI Backend Microservice :8000"]
        API[FastAPI Router Engine]
        AGENTS[Multi-Agent LangGraph Engine]
    end

    subgraph Cache ["In-Memory Cache & Event Bus"]
        REDIS[Redis Store :6379]
    end

    subgraph Database ["Persistent Database"]
        PG[(PostgreSQL / PostGIS :5432)]
    end

    ST -->|HTTP API / WebSockets| API
    API --> AGENTS
    AGENTS -->|Checkpoint State & Queues| REDIS
    API -->|ORM Data Access| PG
```

---

## 2. Multi-Agent Triage & Dispatch Workflow State Machine

The emergency dispatch execution graph is governed by LangGraph. Each node represents a specialized AI agent or deterministic decision module:

```mermaid
stateDiagram-v2
    [*] --> IncidentReported
    IncidentReported --> VisionAnalysis: Trigger Computer Vision Pipeline
    VisionAnalysis --> SeverityAssessment: Extract Hazard Bounding Boxes & Confidence
    SeverityAssessment --> EmergencyRouting: Assign Severity Level (Level 1 - Level 4)
    
    state EmergencyRouting {
        [*] --> HospitalSelection
        HospitalSelection --> AmbulanceDispatch: Match Trauma Level & ICU Availability
        AmbulanceDispatch --> TrafficPreemption: Dispatch ALS Unit & Compute ETA
        TrafficPreemption --> [*]: Preempt Corridor Signals
    }
    
    EmergencyRouting --> ReportGeneration: Compile Audit Logs & Timeline
    ReportGeneration --> PostgreSQLPersistence: Save Incident Report Record
    PostgreSQLPersistence --> [*]: Workflow Execution Completed
```

---

## 3. Data Models & Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o{ INCIDENTS : reports
    USERS ||--o{ RESPONDER_UNITS : operates
    INCIDENTS ||--o{ DISPATCH_ASSIGNMENTS : generates
    RESPONDER_UNITS ||--o{ DISPATCH_ASSIGNMENTS : assigned_to
    INCIDENTS ||--o{ PUBLIC_ALERTS : broadcasts
    INCIDENTS ||--o{ INCIDENT_REPORTS : audited_by

    USERS {
        uuid id PK
        string email
        string hashed_password
        string role
        boolean is_active
    }

    INCIDENTS {
        uuid id PK
        string tracking_code
        int severity
        string status
        float latitude
        float longitude
    }

    RESPONDER_UNITS {
        uuid id PK
        string call_sign
        string unit_type
        string status
        float current_lat
        float current_lon
    }

    DISPATCH_ASSIGNMENTS {
        uuid id PK
        uuid incident_id FK
        uuid unit_id FK
        string status
    }

    INCIDENT_REPORTS {
        uuid id PK
        string incident_id
        string tracking_code
        text ai_summary
        text officer_notes
        json recommendations
        json timeline_data
        json metrics_data
    }
```

---

## 4. Multi-Agent Domain Responsibilities

1. **Supervisor Agent**: Central coordinator managing execution graph state, node transitions, and human-in-the-loop overrides.
2. **Vision Agent**: Processes camera feeds/images via YOLOv11 & heuristic fallback to detect vehicle fires, structural damage, rollover collisions, and chemical vapor clouds.
3. **Severity Agent**: Evaluates victim counts, hazard tags, and spatial density to assign triage severity levels (Level 1 Critical to Level 4 Minor).
4. **Hospital Agent**: Queries regional trauma center network, matches patient injury specialties (Burn, Neuro, Trauma), and reserves ICU beds.
5. **Ambulance Agent**: Computes optimal fleet unit dispatch based on proximity, unit capabilities (ALS, BLS, Hazmat), and ETA.
6. **Traffic Agent**: Preempts traffic signals along the ambulance transit corridor.
7. **Report Agent**: Synthesizes execution logs into formal post-incident reports with AI executive summaries and recommendations.

---

## 5. Security & Resilience Architecture

- **Authentication & RBAC**: JWT access tokens + 7-day refresh tokens signed with HS256 algorithm. Role permissions matrix enforced across API endpoints and Streamlit views (**Admin**, **Police**, **Hospital**, **Dispatcher**, **Viewer**).
- **Offline Resilience**: All Streamlit views and API Service Clients incorporate resilient fallback modes. If backend APIs or WebSockets are disconnected, the system operates seamlessly using local mock data and HTTP polling fallback with zero UI crashes.
