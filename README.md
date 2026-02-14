
<div align="center">

```
 ███╗   ██╗ █████╗ ██╗    ██╗██╗    ██╗ █████╗ ██████╗
 ████╗  ██║██╔══██╗██║    ██║██║    ██║██╔══██╗██╔══██╗
 ██╔██╗ ██║███████║██║ █╗ ██║██║ █╗ ██║███████║██████╔╝
 ██║╚██╗██║██╔══██║██║███╗██║██║███╗██║██╔══██║██╔══██╗
 ██║ ╚████║██║  ██║╚███╔███╔╝╚███╔███╔╝██║  ██║██║  ██║
 ╚═╝  ╚═══╝╚═╝  ╚═╝ ╚══╝╚══╝  ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝
                  ⚡ نـــوّر ⚡
```

# نوّر — Nawwar

### Jordan's AI-Powered Electricity Intelligence Platform
### منصة الذكاء الاصطناعي لقطاع الكهرباء في الأردن

**From Generation to Your Home — من التوليد إلى بيتك**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.x-green.svg)](https://djangoproject.com)
[![AI](https://img.shields.io/badge/AI-Claude_Sonnet_4.5-purple.svg)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## About | نبذة عن المشروع

**Nawwar (نوّر)** is a hybrid AI platform that bridges the gap between power generation and electricity consumers in Jordan. It serves **both** CEGCO operations teams (predictive maintenance, fuel optimization, demand forecasting) **and** everyday consumers (bill scanning, Arabic voice assistant, savings optimization).

**نوّر** هي منصة ذكاء اصطناعي هجينة تربط بين توليد الكهرباء والمستهلك الأردني. تخدم المنصة فِرَق العمليات في شركة الكهرباء المركزية (الصيانة التنبؤية، تحسين الوقود، التنبؤ بالطلب) **والمستهلكين** (مسح الفواتير، المساعد الصوتي العربي، تحسين الاستهلاك).

> Built for the **CEGCO-Sponsored AI Bootcamp** — connecting CEGCO (Central Electricity Generating Company, 51% owned by ACWA Power) with real JEPCO consumer APIs and simulated plant data based on published specifications.

---

## 5 WOW Moments | ٥ لحظات مبهرة

### 1. Bill Photo Scanner — نوّر صورتك
Send a photo of your electricity bill via WhatsApp. GPT-4o Vision extracts every field, validates against JEPCO APIs, and returns a detailed Arabic breakdown with insights.

**أرسل صورة فاتورة الكهرباء عبر واتساب ← تحليل فوري بالعربي مع مقارنة بالاستهلاك السابق**

> Data: **REAL** — JEPCO APIs + GPT-4o Vision

### 2. Arabic Voice Assistant — نوّر صوتك
Send a voice note in Jordanian Arabic. Whisper transcribes it, Claude understands the intent, and Edge-TTS responds in natural Arabic speech. Covers bills, complaints, tariffs, and sector knowledge.

**أرسل رسالة صوتية بالعربي ← نوّر يفهم ويرد صوتياً**

> Data: **REAL** — OpenAI Whisper + Claude Sonnet 4.5 + Edge-TTS

### 3. Save Mode / ToU Optimizer — نوّر وفّر
Analyzes your consumption against EMRC time-of-use tariff periods. Calculates exact savings from load shifting and provides personalized Arabic recommendations.

**تحليل استهلاكك ← حساب التوفير الممكن ← نصائح عربية مخصصة**

> Data: **REAL** — JEPCO bills + EMRC tariff data

### 4. Plant Intelligence Dashboard — نوّر المحطة
Real-time predictive maintenance alerts, heat rate optimization, demand forecasting, and emissions monitoring — all based on CEGCO's actual plant specifications (Aqaba 390MW, Risha 150MW, Rehab 297MW).

**لوحة تحكم ذكية للمحطات: صيانة تنبؤية + تحسين وقود + مراقبة انبعاثات**

> Data: **SIMULATED** — Based on published CEGCO specs, enriched with REAL weather + REAL demand

### 5. Sector Transparency — نوّر السلسلة
AI explains the full electricity chain for the first time: CEGCO generates, NEPCO transmits, JEPCO distributes, your home consumes. Empowering every Jordanian to understand their electricity sector.

**لأول مرة: فهم كامل لسلسلة الكهرباء من المحطة لبيتك**

> Data: **REAL** — Sector knowledge from comprehensive research

---

## Strategic Alignment | التوافق الاستراتيجي

Nawwar directly aligns with **5 national strategies** of Jordan:

| # | Strategy | How Nawwar Aligns |
|---|----------|-------------------|
| 1 | **Jordan Energy Strategy 2020-2030** | Demand-side management through consumer savings optimization and ToU awareness |
| 2 | **Economic Modernization Vision 2022-2033** | Digital transformation of the electricity sector with AI-powered services |
| 3 | **National AI Strategy 2023-2027** | Production AI deployment in a critical infrastructure sector (one of 68 target projects) |
| 4 | **NDC 3.0 (Net-Zero by 2050)** | Emissions monitoring, heat rate optimization, and fuel efficiency tracking |
| 5 | **Electricity Law 2024** | Consumer empowerment, tariff transparency, and regulatory compliance monitoring |

---

## Tech Stack | المجموعة التقنية

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.x + Django REST Framework |
| **Database** | Supabase (PostgreSQL) / SQLite (dev) |
| **AI — Text** | Claude Sonnet 4.5 (Anthropic) |
| **AI — Vision** | GPT-4o Vision (OpenAI) |
| **AI — Voice STT** | OpenAI Whisper |
| **AI — Voice TTS** | Microsoft Edge-TTS (Arabic — ar-JO) |
| **AI — ML** | scikit-learn + Prophet (time-series) |
| **Vector DB** | ChromaDB (RAG knowledge base) |
| **Orchestration** | CrewAI (5 agents, 8 tools) |
| **Messaging** | WhatsApp Business API |
| **Simulation** | NumPy + Pandas (CEGCO plant data) |
| **Dashboard** | Django Templates + Chart.js / Plotly |

---

## Architecture Overview | نظرة عامة على البنية

```
                         ┌─────────────────────────────────┐
                         │         Nawwar Platform          │
                         └────────────┬────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
    ┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
    │   WhatsApp API    │  │   Web Dashboard   │  │    REST API       │
    │   (Webhook)       │  │   (/nawwar/)      │  │   (/api/...)      │
    └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
                         ┌────────────▼────────────────────┐
                         │       Message Router /          │
                         │       LLM Service               │
                         └────────────┬────────────────────┘
                                      │
         ┌────────────┬───────────────┼───────────────┬────────────┐
         │            │               │               │            │
   ┌─────▼─────┐ ┌────▼────┐  ┌──────▼──────┐ ┌──────▼────┐ ┌────▼─────┐
   │  Vision   │ │  Voice  │  │    RAG      │ │ Optimizer │ │  CrewAI  │
   │  Scanner  │ │ Pipeline│  │  Pipeline   │ │  Service  │ │  Agents  │
   │ (GPT-4o) │ │(Whisper)│  │  (Claude)   │ │ (Savings) │ │ (5 crew) │
   └───────────┘ └─────────┘  └──────┬──────┘ └───────────┘ └──────────┘
                                     │
                              ┌──────▼──────┐
                              │  ChromaDB   │
                              │ Knowledge   │
                              │    Base     │
                              └─────────────┘
```

For detailed architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Project Structure | هيكل المشروع

```
nawwar/
├── project/                    # Django project configuration
│   └── settings/
│       ├── base.py             # Shared settings (AI config, CEGCO plants, EMRC tariffs)
│       ├── dev.py              # Development overrides
│       └── prod.py             # Production settings
│
├── apps/
│   ├── core/                   # Base models (TimeStampedModel), utilities
│   ├── users/                  # Custom User model, authentication, profiles
│   │
│   ├── consumer/               # Consumer-facing features
│   │   ├── models/             # Subscription, Bill, Complaint, Tariff, Conversation
│   │   ├── api/                # REST endpoints (bills, tariffs, savings, voice)
│   │   └── selectors/          # Query layer (bill_list, tariff_get_active)
│   │
│   ├── operations/             # CEGCO operations features
│   │   ├── models/             # Plant, Turbine, SensorReading, Maintenance, Emissions
│   │   ├── api/                # REST + ViewSets (plants, turbines, forecasts)
│   │   └── simulators/         # Plant data generators (Aqaba, Risha, Rehab)
│   │
│   ├── ai_engine/              # AI/ML pipeline
│   │   ├── clients/            # OpenAI + Anthropic API clients
│   │   ├── services/           # LLM, RAG, Vision, Voice, Optimizer
│   │   ├── crew/               # CrewAI agents, tools, tasks
│   │   ├── knowledge/          # ChromaDB loader + Arabic chunking
│   │   ├── prompts/            # Prompt templates (bill scanner, RAG, savings)
│   │   └── validators/         # AI output validation
│   │
│   ├── whatsapp/               # WhatsApp Business API integration
│   │   ├── api/                # Webhook endpoint
│   │   ├── clients/            # WhatsApp API client
│   │   └── services/           # Message router
│   │
│   ├── dashboard/              # Web dashboards
│   │   ├── views.py            # Operations + Consumer dashboard views
│   │   └── urls.py             # /nawwar/ routes
│   │
│   └── blog/                   # Content management
│
├── templates/                  # Django templates
├── static/                     # CSS, JS, images
├── knowledge_base/             # Sector documents for RAG
└── requirements/               # Dependency files (base, dev, prod)
```

---

## API Endpoints | نقاط الوصول

### Consumer API (`/api/consumer/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/subscriptions/` | Create subscription |
| GET | `/subscriptions/{number}/` | Get subscription details |
| GET | `/subscriptions/{number}/bills/` | List bills |
| POST | `/bills/scan/` | Scan bill (structured data) |
| POST | `/bills/image-scan/` | Scan bill from photo (GPT-4o Vision) |
| POST | `/bills/analyze/` | AI bill analysis |
| POST | `/query/` | Consumer Q&A (RAG) |
| POST | `/voice/` | Voice query (Whisper + Claude + TTS) |
| POST | `/savings/` | Savings analysis & recommendations |
| GET | `/tariffs/tiers/` | EMRC tariff tiers |
| GET | `/tariffs/periods/` | Time-of-use periods |
| POST | `/complaints/` | File complaint |
| POST | `/conversations/` | Create conversation session |
| GET | `/conversations/{phone}/` | Get conversation |
| GET/POST | `/conversations/{id}/messages/` | Conversation messages |

### Operations API (`/api/operations/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/plants/` | List all CEGCO plants |
| GET | `/plants/{id}/` | Plant details |
| GET | `/turbines/` | List turbines |
| GET | `/sensor-readings/` | Sensor data |
| GET | `/maintenance/` | Maintenance predictions |
| GET | `/emissions/` | Emissions records |
| GET | `/heat-rate/` | Heat rate records |
| GET | `/forecasts/` | Demand forecasts |
| POST | `/anomaly-detection/` | Run anomaly detection |
| GET | `/demand-forecast/` | Generate demand forecast |
| GET | `/emissions-status/{plant}/` | Plant emissions status |
| GET | `/plant-overview/{plant}/` | Plant overview data |
| GET | `/plant-detail/{plant}/` | Detailed plant data |

### WhatsApp Webhook (`/webhook/whatsapp/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/webhook/whatsapp/` | Webhook verification |
| POST | `/webhook/whatsapp/` | Incoming message handler |

### Dashboard (`/nawwar/`)

| Route | Description |
|-------|-------------|
| `/nawwar/operations/` | Operations dashboard (all plants) |
| `/nawwar/operations/{plant}/` | Plant detail view |
| `/nawwar/consumer/` | Consumer AI chat interface |

---

## Data Strategy | استراتيجية البيانات

Nawwar uses a **hybrid data strategy** that combines real and simulated data:

### Real Data (بيانات حقيقية)
- **JEPCO APIs**: 97+ endpoints — consumer bills, consumption history, complaints, meter validation
- **OpenWeatherMap**: Live weather data for Aqaba, Risha, and Amman
- **EMRC Tariffs**: Official tariff tiers, time-of-use periods, fuel adjustment rates
- **NEPCO Statistics**: Annual reports, demand curves, generation statistics

### Simulated Data (بيانات محاكاة)
- **Plant Sensors**: Turbine vibration, temperature, pressure — based on CEGCO's actual published specifications
- **Heat Rate**: Fuel consumption curves by plant type, load%, and ambient temperature
- **Emissions**: NOx/CO2/SOx profiles by fuel type (gas/HFO/LFO) and load percentage
- **Maintenance**: Equipment degradation trends matching published KPIs (91% availability)

### The Bridge (الجسر)
> JEPCO consumer demand (real) **drives** CEGCO generation scheduling (simulated)

---

## Quick Start | البدء السريع

### Prerequisites

- Python 3.13+
- PostgreSQL (or use SQLite for development)
- API keys: OpenAI, Anthropic

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/nawwar.git
cd nawwar

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run migrations
python manage.py migrate

# Load knowledge base into ChromaDB
python manage.py load_knowledge

# Generate simulated plant data
python manage.py simulate_plant_data

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Environment Variables

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
DJANGO_SETTINGS_MODULE=project.settings.dev

# Database (Supabase)
DATABASE_URL=postgresql://user:pass@host:5432/nawwar

# AI Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# WhatsApp Business API
WHATSAPP_TOKEN=your-whatsapp-token
WHATSAPP_VERIFY_TOKEN=nawwar-verify-2024
WHATSAPP_PHONE_NUMBER_ID=your-phone-number-id

# JEPCO
JEPCO_BASE_URL=https://api.jepco.com.jo
```

---

## CEGCO Plant Specifications | مواصفات محطات الكهرباء المركزية

| Plant | Type | Capacity | Fuel | Year | Turbines |
|-------|------|----------|------|------|----------|
| **Aqaba** (العقبة) | Steam | 390 MW | Multi-fuel (HFO/Gas) | 1985 | 5 |
| **Risha** (الريشة) | Gas | 150 MW | Natural Gas | 1989 | 4 |
| **Rehab** (رحاب) | CCGT | 297 MW | Natural Gas | 1990 | 6 |

**Total Capacity: 837 MW** across 3 plants and 15 turbines.

---

## CrewAI Multi-Agent System | نظام الوكلاء المتعددين

Nawwar deploys **5 specialized AI agents** orchestrated by CrewAI:

| Agent | Role | Tools |
|-------|------|-------|
| **Billing Analyst** | Bill analysis, anomaly detection, dispute resolution | BillLookup, TariffLookup, ConsumptionAnalysis |
| **Maintenance Engineer** | Sensor monitoring, failure prediction, maintenance scheduling | SensorData, MaintenancePrediction, Weather |
| **Demand Forecaster** | Load prediction, capacity planning, dispatch optimization | DemandForecast, Weather, SensorData |
| **Energy Advisor** | Personalized savings, efficiency consulting | ConsumptionAnalysis, TariffLookup, BillLookup, Weather |
| **Compliance Officer** | Emissions monitoring, regulatory compliance, reporting | EmissionsLookup, SensorData, DemandForecast |

---

## Jordan's Energy Sector Context | سياق قطاع الطاقة الأردني

- **94%** of energy is imported — making efficiency critical
- **NEPCO** carries **$7B+** in accumulated debt
- Renewable energy target: **29% → 50%** by 2030
- Time-of-use tariffs introduced in **2024**
- **ZERO** production AI systems currently deployed in power generation
- AI energy market projected: **$8.91B → $58.66B** by 2030

Nawwar is positioned to be **Jordan's first production AI platform** for the electricity sector.

---

## Acknowledgments | شكر وتقدير

- **CEGCO** (Central Electricity Generating Company) — Sponsor
- **ACWA Power** — Parent company digital transformation vision
- **JEPCO** (Jordan Electric Power Company) — Consumer API data
- **EMRC** (Energy & Minerals Regulatory Commission) — Tariff data
- **NEPCO** (National Electric Power Company) — Sector statistics

---

<div align="center">

**Built with AI for Jordan's energy future**

**صُنع بالذكاء الاصطناعي لمستقبل الطاقة في الأردن**

</div>
