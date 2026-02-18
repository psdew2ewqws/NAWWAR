> **Copyright (c) 2026 ISSA AL-DALU. All Rights Reserved.**
> This repository is public for competition evaluation only. No license is granted to use, copy, or distribute this code. See [LICENSE](LICENSE) for full terms.

<div align="center">
<pre>
███╗   ██╗ █████╗ ██╗    ██╗██╗    ██╗ █████╗ ██████╗
████╗  ██║██╔══██╗██║    ██║██║    ██║██╔══██╗██╔══██╗
██╔██╗ ██║███████║██║ █╗ ██║██║ █╗ ██║███████║██████╔╝
██║╚██╗██║██╔══██║██║███╗██║██║███╗██║██╔══██║██╔══██╗
██║ ╚████║██║  ██║╚███╔███╔╝╚███╔███╔╝██║  ██║██║  ██║
╚═╝  ╚═══╝╚═╝  ╚═╝ ╚══╝╚══╝  ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝
</pre>

<h1>⚡ نـــوّر ⚡</h1>

### Jordan's AI-Powered Electricity Intelligence Platform
### منصة الذكاء الاصطناعي لقطاع الكهرباء في الأردن

**From Generation to Your Home — من التوليد إلى بيتك**

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.x-green.svg)](https://djangoproject.com)
[![AI](https://img.shields.io/badge/AI-Claude_Sonnet_4.5-purple.svg)](https://anthropic.com)
[![License](https://img.shields.io/badge/License-All_Rights_Reserved-red.svg)](LICENSE)

</div>

---

<div align="center">

## How Electricity Reaches Your Home

</div>

```
 +--------------------------------------------------------------------+
 |                          GENERATION                                |
 |                                                                    |
 |  CEGCO (454 MW) . Samra Electric . AES Jordan . Qatraneh          |
 |            + Renewable Energy Projects (1,575 MW)                  |
 |                                                                    |
 |  CEGCO Owners:                                                     |
 |    40%  Government of Jordan                                       |
 |     9%  Social Security Corporation                                |
 |    33%  ACWA Power (Saudi Arabia)                                  |
 |    13%  Malakoff (Malaysia)                                        |
 |     5%  Consolidated Contractors (CCC)                             |
 |                                                                    |
 +-------------------------------+------------------------------------+
                                 |
                      Sells electricity to
                                 |
                                 v
 +--------------------------------------------------------------------+
 |                         TRANSMISSION                               |
 |                                                                    |
 |                NEPCO -- The Single Buyer                           |
 |          100% Government-Owned . Grid Operator                     |
 |    5,879 km lines . 14,969 MVA . 132kV + 400kV                    |
 |                                                                    |
 |  Buys ALL electricity from generators at fixed prices              |
 |  Sells to distribution companies at regulated rates                |
 |  Accumulated debt: $7B+ (Jordan's energy burden)                   |
 |                                                                    |
 +-------------------------------+------------------------------------+
                                 |
                      Sells electricity to
                                 |
                                 v
 +--------------------------------------------------------------------+
 |                         DISTRIBUTION                               |
 |                                                                    |
 |  JEPCO (Central)     IDECO (North)      EDCO (South)              |
 |  64% of consumers    ~20% of consumers  ~16% of consumers         |
 |  Amman/Zarqa/Salt    Irbid region       Southern Jordan           |
 |  Madaba              Est. 1957          Est. 1962                 |
 |  Est. 1938                                                         |
 |                                                                    |
 |  JEPCO Owners (Amman Stock Exchange -- JOEP):                      |
 |    20.79%  Social Security Corporation                             |
 |     2.59%  Samir A. Barakat                                        |
 |     2.01%  Government of Jordan                                    |
 |     1.47%  Issam Bdair                                             |
 |     1.39%  Fares Al-Mouasher                                       |
 |    ~72%    Public float (thousands of investors)                   |
 |                                                                    |
 +-------------------------------+------------------------------------+
                                 |
                            Delivers to
                                 |
                                 v
 +--------------------------------------------------------------------+
 |                          CONSUMERS                                 |
 |                                                                    |
 |                  ~2.6 Million Households                           |
 |                                                                    |
 |  Residential (Subsidized) . Commercial . Industrial                |
 |  Agricultural . Hotels . Government . EV Charging                  |
 |                                                                    |
 |  Tariff set by EMRC (government regulator)                         |
 |  Subsidized residential: 50 / 100 / 200 fils per kWh              |
 |                                                                    |
 +--------------------------------------------------------------------+

                      Nawwar sees the FULL chain
                   from generation to your home
```

<div align="center">

### The Regulators

| Entity | Role | Type |
|:------:|:----:|:----:|
| **EMRC** | Sets tariff rates, regulates the sector | Government body |
| **MEMR** | Ministry of Energy & Mineral Resources — policy maker | Government ministry |
| **NEPCO** | Transmission monopoly, single buyer | 100% Government-owned |

</div>

---

<div align="center">

## What is Nawwar? | ما هو نوّر؟

</div>

**Nawwar (نوّر)** is a hybrid AI platform that bridges the gap between power generation and electricity consumers in Jordan. It serves **both** CEGCO operations teams (predictive maintenance, fuel optimization, demand forecasting) **and** everyday consumers (bill scanning, Arabic voice assistant, savings optimization).

**نوّر** هي منصة ذكاء اصطناعي هجينة تربط بين توليد الكهرباء والمستهلك الأردني. تخدم المنصة فِرَق العمليات في شركة الكهرباء المركزية (الصيانة التنبؤية، تحسين الوقود، التنبؤ بالطلب) **والمستهلكين** (مسح الفواتير، المساعد الصوتي العربي، تحسين الاستهلاك).

> Built for the **CEGCO-Sponsored AI Bootcamp** — February 2026

---

<div align="center">

## Features | المميزات

</div>

### 1. Bill Photo Scanner — نوّر صورتك
Send a photo of your electricity bill via WhatsApp. GPT-4o Vision extracts every field, validates against  APIs, and returns a detailed Arabic breakdown with insights.

**أرسل صورة فاتورة الكهرباء عبر واتساب ← تحليل فوري بالعربي مع مقارنة بالاستهلاك السابق**

### 2. Arabic Voice Assistant — نوّر صوتك
Send a voice note in Jordanian Arabic. Whisper transcribes it, Claude understands the intent, and Edge-TTS responds in natural Arabic speech. Covers bills, complaints, tariffs, and sector knowledge.

**أرسل رسالة صوتية بالعربي ← نوّر يفهم ويرد صوتياً**

### 3. Save Mode / ToU Optimizer — نوّر وفّر
Analyzes your consumption against EMRC time-of-use tariff periods. Calculates exact savings from load shifting and provides personalized Arabic recommendations.

**تحليل استهلاكك ← حساب التوفير الممكن ← نصائح عربية مخصصة**

### 4. Plant Intelligence Dashboard — نوّر المحطة
Real-time predictive maintenance alerts, heat rate optimization, demand forecasting, and emissions monitoring — all based on CEGCO's actual plant specifications (Aqaba 390MW, Risha 150MW, Rehab 297MW).

**لوحة تحكم ذكية للمحطات: صيانة تنبؤية + تحسين وقود + مراقبة انبعاثات**

### 5. Sector Transparency — نوّر السلسلة
AI explains the full electricity chain for the first time: CEGCO generates, NEPCO transmits,  distributes, your home consumes. Empowering every Jordanian to understand their electricity sector.

**لأول مرة: فهم كامل لسلسلة الكهرباء من المحطة لبيتك**

---

<div align="center">

## Strategic Alignment | التوافق الاستراتيجي

</div>

Nawwar directly aligns with **5 national strategies** of Jordan:

| # | Strategy | How Nawwar Aligns |
|---|----------|-------------------|
| 1 | **Jordan Energy Strategy 2020-2030** | Demand-side management through consumer savings optimization and ToU awareness |
| 2 | **Economic Modernization Vision 2022-2033** | Digital transformation of the electricity sector with AI-powered services |
| 3 | **National AI Strategy 2023-2027** | Production AI deployment in a critical infrastructure sector (one of 68 target projects) |
| 4 | **NDC 3.0 (Net-Zero by 2050)** | Emissions monitoring, heat rate optimization, and fuel efficiency tracking |
| 5 | **Electricity Law 2024** | Consumer empowerment, tariff transparency, and regulatory compliance monitoring |

---

<div align="center">

## Tech Stack | المجموعة التقنية

</div>

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

<div align="center">

## Architecture | البنية

</div>

<div align="center">
<pre>
                    ┌─────────────────────────────────┐
                    │         Nawwar Platform          │
                    └────────────┬────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
│   WhatsApp API   │  │   Web Dashboard   │  │    REST API       │
│   (Webhook)      │  │   (/nawwar/)      │  │   (/api/...)      │
└────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
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
┌───▼─────┐ ┌───▼────┐  ┌──────▼──────┐ ┌──────▼────┐ ┌─────▼────┐
│ Vision  │ │ Voice  │  │    RAG      │ │ Optimizer │ │  CrewAI  │
│ Scanner │ │Pipeline│  │  Pipeline   │ │  Service  │ │  Agents  │
│(GPT-4o) │ │(Whisper│  │  (Claude)   │ │ (Savings) │ │ (5 crew) │
└─────────┘ └────────┘  └──────┬──────┘ └───────────┘ └──────────┘
                               │
                        ┌──────▼──────┐
                        │  ChromaDB   │
                        │ Knowledge   │
                        │    Base     │
                        └─────────────┘
</pre>
</div>

For detailed architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

<div align="center">

## Data Strategy | استراتيجية البيانات

</div>

### Real Data (بيانات حقيقية)
- **Smart Meter Integration**: Real-time daily consumption, bill estimates, meter readings
- **OpenWeatherMap**: Live weather data for Aqaba, Risha, and Amman
- **EMRC Tariffs**: Official 2024 tariff tiers validated against jepco.com.jo
- **NEPCO Statistics**: Annual reports, demand curves, generation statistics

### Simulated Data (بيانات محاكاة)
- **Plant Sensors**: Turbine vibration, temperature, pressure — based on CEGCO's published specs
- **Heat Rate**: Fuel consumption curves by plant type, load%, and ambient temperature
- **Emissions**: NOx/CO2/SOx profiles by fuel type (gas/HFO/LFO) and load percentage
- **Maintenance**: Equipment degradation trends matching published KPIs (91% availability)

### The Bridge (الجسر)
>  consumer demand (real) **drives** CEGCO generation scheduling (simulated)

---

<div align="center">

## CEGCO Plant Specifications | مواصفات المحطات

</div>

| Plant | Type | Capacity | Fuel | Year | Turbines |
|:-----:|:----:|:--------:|:----:|:----:|:--------:|
| **Aqaba** (العقبة) | Steam | 390 MW | Multi-fuel (HFO/Gas) | 1985 | 5 |
| **Risha** (الريشة) | Gas | 150 MW | Natural Gas | 1989 | 4 |
| **Rehab** (رحاب) | CCGT | 297 MW | Natural Gas | 1990 | 6 |

**Total: 837 MW** across 3 plants and 15 turbines.

---

<div align="center">

## CrewAI Multi-Agent System | نظام الوكلاء المتعددين

</div>

| Agent | Role | Tools |
|:-----:|:----:|:-----:|
| **Billing Analyst** | Bill analysis, anomaly detection | BillLookup, TariffLookup, ConsumptionAnalysis |
| **Maintenance Engineer** | Sensor monitoring, failure prediction | SensorData, MaintenancePrediction, Weather |
| **Demand Forecaster** | Load prediction, capacity planning | DemandForecast, Weather, SensorData |
| **Energy Advisor** | Personalized savings consulting | ConsumptionAnalysis, TariffLookup, BillLookup |
| **Compliance Officer** | Emissions monitoring, regulatory compliance | EmissionsLookup, SensorData, DemandForecast |

---

<div align="center">

## Jordan's Energy Context | سياق الطاقة في الأردن

</div>

- **94%** of energy is imported — making efficiency critical
- **NEPCO** carries **$7B+** in accumulated debt
- Renewable energy target: **29% → 50%** by 2030
- Time-of-use tariffs introduced in **2024**
- **ZERO** production AI systems currently deployed in power generation
- AI energy market projected: **$8.91B → $58.66B** by 2030

Nawwar is positioned to be **Jordan's first production AI platform** for the electricity sector.

---

<div align="center">

**Built for Jordan's energy future**

**ISSA AL-DALU | CEGCO AI Bootcamp | February 2026**

</div>
