# Architecture — Nawwar (نوّر)

Technical architecture documentation for Jordan's AI-Powered Electricity Intelligence Platform.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Django Application Structure](#django-application-structure)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [AI Pipeline Architecture](#ai-pipeline-architecture)
6. [Database Schema](#database-schema)
7. [External Integrations](#external-integrations)
8. [CrewAI Multi-Agent System](#crewai-multi-agent-system)
9. [Security & Configuration](#security--configuration)

---

## System Overview

Nawwar is a **Django 5.x monolith** with a modular app architecture. It serves three interface channels (WhatsApp, Web Dashboard, REST API) that converge into a unified AI engine.

**Key Design Decisions:**
- **Monolith over microservices** — Simpler deployment, shared ORM, faster iteration
- **Async AI services** — All LLM/Vision/Voice calls are async for concurrency
- **Selector pattern** — Read queries isolated from models for clean separation
- **Service layer** — Business logic lives in services, not views or models
- **Multi-provider AI** — Anthropic (text), OpenAI (vision/STT/embeddings), Edge-TTS (synthesis)

---

## High-Level Architecture

```
 ┌────────────────────────────────────────────────────────────────────┐
 │                        ENTRY POINTS                               │
 │                                                                    │
 │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
 │  │  WhatsApp    │   │     Web      │   │      REST API        │   │
 │  │  Business    │   │  Dashboard   │   │  (DRF ViewSets)      │   │
 │  │  Webhook     │   │  /nawwar/    │   │  /api/consumer/      │   │
 │  │              │   │              │   │  /api/operations/    │   │
 │  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘   │
 │         │                  │                      │               │
 └─────────┼──────────────────┼──────────────────────┼───────────────┘
           │                  │                      │
           ▼                  ▼                      ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │                     ROUTING & ORCHESTRATION                        │
 │                                                                    │
 │  ┌─────────────────────┐    ┌──────────────────────────────────┐   │
 │  │   MessageRouter     │    │         LLMService               │   │
 │  │   (WhatsApp)        │    │   (Web/API unified entry)        │   │
 │  │                     │    │                                  │   │
 │  │ • _handle_text()    │    │ • route_request()                │   │
 │  │ • _handle_image()   │    │   → text → RAG                  │   │
 │  │ • _handle_audio()   │    │   → image → Vision              │   │
 │  │ • _handle_location()│    │   → audio → Whisper → RAG       │   │
 │  │ • _detect_intent()  │    │                                  │   │
 │  └────────┬────────────┘    └──────────────┬───────────────────┘   │
 │           │                                │                       │
 └───────────┼────────────────────────────────┼───────────────────────┘
             │                                │
             ▼                                ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │                        AI SERVICES LAYER                           │
 │                                                                    │
 │  ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌──────────────┐  │
 │  │  Vision    │ │   Voice    │ │     RAG      │ │  Savings     │  │
 │  │  Service   │ │  Service   │ │   Service    │ │  Optimizer   │  │
 │  │            │ │            │ │              │ │              │  │
 │  │ scan_bill()│ │transcribe()│ │ answer()     │ │ analyze()    │  │
 │  │ analyze()  │ │synthesize()│ │ classify()   │ │ calculate()  │  │
 │  │            │ │ pipeline() │ │              │ │ recommend()  │  │
 │  └──────┬─────┘ └─────┬──────┘ └──────┬───────┘ └──────┬───────┘  │
 │         │             │               │                │          │
 │  ┌──────▼─────────────▼───────────────▼────────────────▼───────┐  │
 │  │                    AI CLIENTS                                │  │
 │  │                                                              │  │
 │  │  ┌─────────────────┐   ┌──────────────────┐                 │  │
 │  │  │  OpenAIClient   │   │ AnthropicClient  │                 │  │
 │  │  │                 │   │                  │                 │  │
 │  │  │ • vision (4o)   │   │ • chat (Sonnet)  │                 │  │
 │  │  │ • whisper (STT) │   │ • system prompts │                 │  │
 │  │  │ • embeddings    │   │                  │                 │  │
 │  │  └─────────────────┘   └──────────────────┘                 │  │
 │  └──────────────────────────────────────────────────────────────┘  │
 │                                                                    │
 │  ┌──────────────────────────────────────────────────────────────┐  │
 │  │                    CrewAI Orchestration                       │  │
 │  │                                                              │  │
 │  │  Billing ─── Maintenance ─── Forecaster ─── Advisor ─── Compliance │
 │  │  Agent       Agent           Agent          Agent        Agent     │
 │  │    │            │              │              │            │       │
 │  │    └────────────┴──────────────┴──────────────┴────────────┘       │
 │  │                         8 Custom Tools                             │
 │  └──────────────────────────────────────────────────────────────┘  │
 │                                                                    │
 └────────────────────────────────────────────────────────────────────┘
             │                                │
             ▼                                ▼
 ┌────────────────────────┐    ┌──────────────────────────────────────┐
 │      ChromaDB          │    │         PostgreSQL / SQLite          │
 │   (Vector Store)       │    │                                      │
 │                        │    │  Consumer: Subscription, Bill,       │
 │  • Sector documents    │    │    Complaint, Tariff, Conversation   │
 │  • Arabic chunking     │    │                                      │
 │  • Semantic search     │    │  Operations: Plant, Turbine,         │
 │                        │    │    SensorReading, Maintenance,       │
 │                        │    │    Emissions, HeatRate, Forecast     │
 └────────────────────────┘    │                                      │
                               │  AI: AILog (audit trail)             │
                               └──────────────────────────────────────┘
```

---

## Django Application Structure

### 8 Django Apps

| App | Purpose | Key Components |
|-----|---------|----------------|
| **core** | Base models and utilities | `TimeStampedModel` base class, shared helpers |
| **users** | Authentication and profiles | Custom `User` model, `UserProfile`, login/register views |
| **consumer** | Consumer-facing features | Subscription, Bill, Complaint, Tariff, Conversation models |
| **operations** | CEGCO plant operations | Plant, Turbine, SensorReading, Maintenance, Emissions models |
| **ai_engine** | AI/ML pipeline | LLM clients, RAG, Vision, Voice, CrewAI agents |
| **whatsapp** | WhatsApp integration | Webhook, MessageRouter, WhatsApp API client |
| **dashboard** | Web dashboards | Operations monitoring, Consumer AI chat |
| **blog** | Content management | Sector articles and educational content |

### Application Dependencies

```
users ──────────┐
                │
core ───────────┼─── consumer ───┐
                │                │
                ├─── operations ─┤
                │                │
                └────────────────┼─── ai_engine ─── whatsapp
                                 │
                                 └─── dashboard
```

---

## Data Flow Diagrams

### Flow 1: Consumer Bill Scan via WhatsApp

```
Consumer                WhatsApp         Nawwar                   GPT-4o       Smart Meter
   │                      API            Server                   Vision          API
   │                       │               │                        │              │
   │  Send bill photo      │               │                        │              │
   │──────────────────────▶│               │                        │              │
   │                       │  Webhook POST │                        │              │
   │                       │──────────────▶│                        │              │
   │                       │               │                        │              │
   │                       │               │  Download media        │              │
   │                       │◀──────────────│                        │              │
   │                       │──────────────▶│                        │              │
   │                       │               │                        │              │
   │                       │               │  Extract bill fields   │              │
   │                       │               │───────────────────────▶│              │
   │                       │               │◀───────────────────────│              │
   │                       │               │   Structured JSON      │              │
   │                       │               │                        │              │
   │                       │               │  Validate subscriber   │              │
   │                       │               │─────────────────────────────────────▶│
   │                       │               │◀─────────────────────────────────────│
   │                       │               │                        │              │
   │                       │  Arabic reply │                        │              │
   │                       │◀──────────────│                        │              │
   │  Bill analysis in     │               │                        │              │
   │  Arabic with insights │               │                        │              │
   │◀──────────────────────│               │                        │              │
```

### Flow 2: Voice Assistant Pipeline

```
Consumer        WhatsApp      MessageRouter     Whisper      RAGService     Edge-TTS
   │               │               │               │             │             │
   │ Voice note    │               │               │             │             │
   │──────────────▶│  POST         │               │             │             │
   │               │──────────────▶│               │             │             │
   │               │               │               │             │             │
   │               │               │  Transcribe   │             │             │
   │               │               │──────────────▶│             │             │
   │               │               │  Arabic text  │             │             │
   │               │               │◀──────────────│             │             │
   │               │               │               │             │             │
   │               │               │  Classify intent            │             │
   │               │               │  + RAG answer ─────────────▶│             │
   │               │               │◀────────────────────────────│             │
   │               │               │               │             │             │
   │               │               │  Synthesize Arabic speech   │             │
   │               │               │───────────────────────────────────────────▶│
   │               │               │◀──────────────────────────────────────────│
   │               │               │               │             │             │
   │               │  Text + Audio │               │             │             │
   │               │◀──────────────│               │             │             │
   │ Response      │               │               │             │             │
   │◀──────────────│               │               │             │             │
```

### Flow 3: Predictive Maintenance Pipeline

```
Plant Simulator     SensorReading DB     Anomaly Detector     MaintenancePrediction
      │                    │                    │                       │
      │  Generate data     │                    │                       │
      │  (management cmd)  │                    │                       │
      │───────────────────▶│                    │                       │
      │                    │                    │                       │
      │                    │  Latest readings   │                       │
      │                    │───────────────────▶│                       │
      │                    │                    │                       │
      │                    │                    │  IsolationForest      │
      │                    │                    │  anomaly detection    │
      │                    │                    │                       │
      │                    │                    │  Anomaly detected     │
      │                    │                    │──────────────────────▶│
      │                    │                    │                       │
      │                    │                    │  Map to failure type  │
      │                    │                    │  + severity           │
      │                    │                    │──────────────────────▶│
      │                    │                    │                       │
      │                    │                    │                       │  Alert on
      │                    │                    │                       │  Dashboard
```

### Flow 4: Demand Forecasting

```
Consumer            OpenWeather       DemandForecaster      Generation
Demand (Real)        API (Real)       (Ridge Regression)     Schedule
     │                  │                    │                    │
     │  Historical      │                    │                    │
     │  demand data     │                    │                    │
     │─────────────────────────────────────▶│                    │
     │                  │                    │                    │
     │                  │  Temperature,      │                    │
     │                  │  humidity           │                    │
     │                  │───────────────────▶│                    │
     │                  │                    │                    │
     │                  │                    │  Time features +   │
     │                  │                    │  weather → predict  │
     │                  │                    │                    │
     │                  │                    │  Forecast + CI     │
     │                  │                    │───────────────────▶│
     │                  │                    │                    │
     │                  │                    │         Schedule generation
     │                  │                    │         across plants
```

---

## AI Pipeline Architecture

### Multi-Provider AI Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Engine                                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    LLMService                             │    │
│  │           (Unified routing by message type)               │    │
│  └────────────────────────┬──────────────────────────────────┘    │
│                           │                                      │
│         ┌─────────────────┼─────────────────┐                    │
│         │                 │                 │                    │
│    ┌────▼────┐      ┌─────▼─────┐     ┌─────▼─────┐            │
│    │  text   │      │  image    │     │  audio    │            │
│    └────┬────┘      └─────┬─────┘     └─────┬─────┘            │
│         │                 │                 │                    │
│    ┌────▼────────┐  ┌─────▼──────┐   ┌──────▼──────┐           │
│    │ RAGService  │  │VisionSvc   │   │ VoiceSvc    │           │
│    │             │  │            │   │             │           │
│    │ 1. Search   │  │ 1. GPT-4o  │   │ 1. Whisper  │           │
│    │    ChromaDB │  │    extract │   │    STT      │           │
│    │ 2. Build    │  │ 2. Validate│   │ 2. Classify │           │
│    │    context  │  │    fields  │   │    intent   │           │
│    │ 3. Claude   │  │ 3. Map to  │   │ 3. RAG     │           │
│    │    answer   │  │    schema  │   │    answer   │           │
│    │ 4. Validate │  │            │   │ 4. Edge-TTS │           │
│    │    output   │  │            │   │    synth    │           │
│    └─────────────┘  └────────────┘   └─────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                  Knowledge Base (ChromaDB)                │    │
│  │                                                           │    │
│  │  Documents:                                               │    │
│  │  • CEGCO Intelligence Report                              │    │
│  │  • Distribution API Documentation                          │    │
│  │  • Jordan Energy Sector Analysis                          │    │
│  │  • EMRC Tariff Regulations                                │    │
│  │  • NEPCO Annual Reports                                   │    │
│  │                                                           │    │
│  │  Processing:                                              │    │
│  │  • Arabic-aware text chunking                             │    │
│  │  • OpenAI text-embedding-3-small                          │    │
│  │  • Semantic similarity search                             │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │               Prompt Engineering                          │    │
│  │                                                           │    │
│  │  • SYSTEM_PROMPT_AR — Arabic AI persona                   │    │
│  │  • CONSUMER_QA_PROMPT — Bill/tariff Q&A                   │    │
│  │  • OPERATIONS_QA_PROMPT — Plant/maintenance Q&A           │    │
│  │  • BILL_EXTRACTION_PROMPT — Vision OCR instructions       │    │
│  │  • BILL_ANALYSIS_PROMPT — Consumption insights            │    │
│  │  • SAVINGS_PROMPT — Personalized recommendations          │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │               Output Validation                           │    │
│  │                                                           │    │
│  │  • validate_ai_response() — sanitize LLM text output     │    │
│  │  • validate_bill_scan() — verify extracted bill fields    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Intent Classification

The RAG service classifies user intent using bilingual keyword scoring:

| Intent | Arabic Keywords | English Keywords |
|--------|----------------|-----------------|
| billing | فاتورة, مبلغ, دفع, رصيد | bill, amount, pay, balance |
| tariff | تعرفة, شريحة, سعر | tariff, tier, rate |
| outage | انقطاع, عطل, كهرباء مقطوعة | outage, fault, power cut |
| complaint | شكوى, مشكلة, عداد | complaint, problem, meter |
| savings | توفير, تخفيض, نصائح | save, reduce, tips |
| operations | محطة, توربين, صيانة | plant, turbine, maintenance |

Complex intents (billing, savings, operations) may trigger **CrewAI multi-agent analysis** for deeper investigation.

---

## Database Schema

### Consumer Domain

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Subscription   │     │      Bill        │     │  BillLineItem    │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ subscriber_number│────▶│ subscription_id  │────▶│ bill_id          │
│ subscription_type│     │ billing_period_* │     │ description      │
│ owner_name       │     │ total_kwh        │     │ description_ar   │
│ phone_number     │     │ peak_kwh         │     │ amount_fils      │
│ address          │     │ off_peak_kwh     │     │ tariff_tier      │
│ status           │     │ total_amount_fils│     └──────────────────┘
└──────────────────┘     │ previous_reading │
                         │ current_reading  │
                         └──────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    Complaint     │     │   TariffTier     │     │  TariffPeriod    │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ subscription_id  │     │ sector           │     │ name             │
│ category         │     │ tier_number      │     │ start_hour       │
│ description      │     │ min_kwh          │     │ end_hour         │
│ status           │     │ max_kwh          │     │ is_peak          │
│ priority         │     │ rate_fils        │     │ multiplier       │
└──────────────────┘     └──────────────────┘     └──────────────────┘

┌──────────────────┐     ┌──────────────────┐
│ConversationSession│    │    Message       │
├──────────────────┤     ├──────────────────┤
│ phone_number     │────▶│ session_id       │
│ channel          │     │ role             │
│ language         │     │ content          │
│ is_active        │     │ message_type     │
└──────────────────┘     │ intent           │
                         └──────────────────┘
```

### Operations Domain

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│      Plant       │     │     Turbine      │     │  SensorReading   │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ code (unique)    │────▶│ plant_id         │────▶│ turbine_id       │
│ name / name_ar   │     │ turbine_number   │     │ timestamp        │
│ plant_type       │     │ model            │     │ sensor_type      │
│  (steam/gas/ccgt)│     │ capacity_mw      │     │ value            │
│ fuel_type        │     │ status           │     │ unit             │
│ capacity_mw      │     │ efficiency_%     │     │ is_anomaly       │
│ commissioned_year│     └──────────────────┘     └──────────────────┘
│ lat / lon        │
│ status           │     ┌──────────────────┐     ┌──────────────────┐
│ current_load_mw  │     │MaintenancePred.  │     │ EmissionsRecord  │
│ efficiency_%     │     ├──────────────────┤     ├──────────────────┤
└──────────────────┘     │ turbine_id       │     │ plant_id         │
                         │ prediction_type  │     │ timestamp        │
                         │ severity         │     │ co2_tons         │
                         │ predicted_date   │     │ nox_kg           │
                         │ confidence       │     │ so2_kg           │
                         │ description      │     │ load_mw          │
                         │ is_acknowledged  │     │ compliant        │
                         └──────────────────┘     └──────────────────┘

┌──────────────────┐     ┌──────────────────┐
│  HeatRateRecord  │     │  DemandForecast  │
├──────────────────┤     ├──────────────────┤
│ plant_id         │     │ forecast_hour    │
│ timestamp        │     │ predicted_mw     │
│ heat_rate_btu    │     │ confidence       │
│ fuel_consumption │     │ actual_mw        │
│ load_mw          │     │ model_version    │
│ efficiency_%     │     └──────────────────┘
└──────────────────┘
```

### AI Domain

```
┌──────────────────┐
│      AILog       │
├──────────────────┤
│ model_name       │   Audit trail for all AI API calls
│ provider         │   (openai / anthropic / local)
│ task_type        │   (chat / vision / stt / tts / embedding)
│ latency_ms       │
│ tokens_used      │
│ success          │
│ error_message    │
└──────────────────┘
```

---

## External Integrations

### Smart Meter Integration (Real Data)

```
┌────────────────────────────────────────────┐
│       Distribution Company Integration     │
│                                            │
│  • Real-time smart meter consumption       │
│  • Daily kWh readings per subscriber       │
│  • Bill projections and comparisons        │
│  • Historical usage patterns               │
│                                            │
└────────────────────────────────────────────┘
```

### OpenWeatherMap API (Real Data)

```
┌──────────────────────────────────┐
│     OpenWeatherMap Integration   │
│                                  │
│  Locations:                      │
│  • Aqaba (29.52°N, 35.00°E)     │
│  • Risha (32.25°N, 38.25°E)     │
│  • Amman (31.95°N, 35.93°E)     │
│                                  │
│  Usage:                          │
│  • Temperature → demand correlation│
│  • Ambient temp → plant efficiency │
│  • Weather → maintenance scheduling│
└──────────────────────────────────┘
```

### WhatsApp Business API

```
┌──────────────────────────────────────────┐
│         WhatsApp Integration             │
│                                          │
│  Webhook: /webhook/whatsapp/ (POST/GET)  │
│                                          │
│  Inbound:                                │
│  • Text messages → intent → RAG/CrewAI   │
│  • Image messages → bill scan            │
│  • Audio messages → voice pipeline       │
│  • Location → nearest JEPCO office       │
│                                          │
│  Outbound:                               │
│  • WhatsAppClient.send_text()            │
│  • WhatsAppClient.send_audio()           │
│  • WhatsAppClient.download_media()       │
│                                          │
│  API: graph.facebook.com/v18.0           │
└──────────────────────────────────────────┘
```

### AI Provider APIs

```
┌────────────────────────┐  ┌─────────────────────────┐  ┌──────────────────┐
│   Anthropic API        │  │     OpenAI API           │  │  Edge-TTS        │
│                        │  │                          │  │  (Local/Free)    │
│  Model:                │  │  Models:                 │  │                  │
│  claude-sonnet-4-5     │  │  • gpt-4o (vision)       │  │  Voices:         │
│                        │  │  • whisper-1 (STT)       │  │  • ar-JO-Taimur  │
│  Uses:                 │  │  • text-embedding-3-small│  │  • ar-JO-Sana    │
│  • RAG Q&A             │  │                          │  │                  │
│  • Savings advice      │  │  Uses:                   │  │  Uses:           │
│  • Intent processing   │  │  • Bill photo scanning   │  │  • Arabic speech │
│                        │  │  • Audio transcription   │  │    synthesis     │
│  Config: AI_CONFIG     │  │  • Vector embeddings     │  │                  │
│  Temp: 0.3             │  │                          │  │                  │
│  Max tokens: 4096      │  │                          │  │                  │
└────────────────────────┘  └──────────────────────────┘  └──────────────────┘
```

---

## CrewAI Multi-Agent System

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CrewAI Orchestration Layer                         │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │   Billing   │  │ Maintenance │  │  Demand     │                  │
│  │   Analyst   │  │  Engineer   │  │ Forecaster  │                  │
│  │             │  │             │  │             │                  │
│  │ Tools:      │  │ Tools:      │  │ Tools:      │                  │
│  │ • BillLookup│  │ • SensorData│  │ • Demand    │                  │
│  │ • Tariff    │  │ • Maint.    │  │   Forecast  │                  │
│  │ • Analysis  │  │ • Weather   │  │ • Weather   │                  │
│  │             │  │             │  │ • Sensor    │                  │
│  │ Delegation: │  │ Delegation: │  │ Delegation: │                  │
│  │    Yes      │  │    Yes      │  │    Yes      │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐                                   │
│  │   Energy    │  │ Compliance  │                                   │
│  │   Advisor   │  │  Officer    │                                   │
│  │             │  │             │                                   │
│  │ Tools:      │  │ Tools:      │                                   │
│  │ • Analysis  │  │ • Emissions │                                   │
│  │ • Tariff    │  │ • Sensor    │                                   │
│  │ • Bill      │  │ • Forecast  │                                   │
│  │ • Weather   │  │             │                                   │
│  │             │  │ Delegation: │                                   │
│  │ Delegation: │  │    No       │                                   │
│  │    No       │  │             │                                   │
│  └─────────────┘  └─────────────┘                                   │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │                     8 Custom CrewAI Tools                      │   │
│  │                                                               │   │
│  │  BillLookupTool ─── TariffLookupTool ─── SensorDataTool      │   │
│  │  ConsumptionAnalysisTool ─── MaintenancePredictionTool        │   │
│  │  EmissionsLookupTool ─── DemandForecastTool ─── WeatherTool   │   │
│  │                                                               │   │
│  │  Each tool wraps existing Django selectors/services            │   │
│  │  to expose them as CrewAI-compatible interfaces                │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### When CrewAI is Triggered

The WhatsApp MessageRouter escalates to CrewAI for complex intents:
- **billing** — When a subscriber number is detected in the message
- **savings** — For personalized consumption analysis
- **operations** — For plant-specific technical queries

Simple queries (tariff info, outage reports, general Q&A) are handled directly by the RAG pipeline.

---

## Security & Configuration

### Settings Architecture

```
project/settings/
├── base.py      # Shared: INSTALLED_APPS, AI_CONFIG, CEGCO_PLANTS, EMRC_TARIFFS
├── dev.py       # DEBUG=True, SQLite, verbose logging
└── prod.py      # DEBUG=False, PostgreSQL, security headers
```

### Key Security Measures

- **python-decouple** for environment variable management
- **DRF throttling**: 30 req/min (anon), 120 req/min (auth), 10 req/min (AI)
- **CSRF protection** on all form-based views
- **Session authentication** for API access
- **AI output validation** — all LLM responses pass through `validate_ai_response()`
- **Bill scan validation** — `validate_bill_scan()` verifies extracted fields
- **WhatsApp webhook verification** via verify token

### Configuration Constants

CEGCO plant specifications, EMRC tariff tiers, AI model configurations, and TTS voice settings are all centralized in `base.py` for maintainability and transparency.

---

## Plant Data Simulation

### How Simulated Data is Generated

Each CEGCO plant has a dedicated simulator based on published specifications:

```
management command: simulate_plant_data
    │
    ├── Aqaba Simulator (390MW Steam, 1985)
    │   ├── 5 turbines × sensor readings
    │   ├── HFO/gas fuel curves by load%
    │   ├── Temperature-dependent efficiency
    │   └── Anomaly injection (vibration, bearing temp)
    │
    ├── Risha Simulator (150MW Gas, 1989)
    │   ├── 4 turbines × sensor readings
    │   ├── Natural gas consumption curves
    │   ├── Desert ambient temperature effects
    │   └── Anomaly injection (compressor, flame)
    │
    └── Rehab Simulator (297MW CCGT, 1990)
        ├── 6 turbines (gas + steam) × sensor readings
        ├── Combined cycle efficiency curves
        ├── Dual-pressure HRSG modeling
        └── Anomaly injection (HRSG, steam path)

Published KPIs matched:
• 91% availability (vs 95% benchmark)
• 206 days downtime over 8 years
• Fuel mix: HFO/natural gas/LFO
```

---

*For the project README, see [README.md](README.md).*
