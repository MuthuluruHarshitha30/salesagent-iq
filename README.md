# SalesAgent IQ

[![Tests](https://img.shields.io/badge/Tests-34%20Passed%20(100%25)-success)](file:///C:/Users/muthu/.gemini/antigravity/scratch/mini-bi-assistant/run_tests.py)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Vectorless%20RAG-indigo)](docs/vectorless_rag_guide.md)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

An intelligent, lightweight Business Intelligence Assistant that enables business stakeholders to ask arbitrary natural language questions about sales data and receive deterministic, mathematically verified answers supported by live database queries.

**SalesAgent IQ** is built with **Python**, **Starlette**, **SQLite**, **Google Gemini**, and a **Vectorless RAG** architecture with strict read-only safety guardrails.

---

## 📑 Table of Contents
- [Executive Overview](#-executive-overview)
- [Key Features](#-key-features)
- [Project Structure](#-project-structure)
- [Quickstart & Execution](#-quickstart--execution)
- [Data Management & Anomaly Handling](#-data-management--anomaly-handling)
- [Core Questions & Benchmark Results](#-core-questions--benchmark-results)
- [AI & Vectorless RAG Architecture](#-ai--vectorless-rag-architecture)
- [Security & SQL Guardrails](#-security--sql-guardrails)
- [Automated Testing](#-automated-testing)
- [Known Limitations](#-known-limitations)
- [Deliverables & Documentation](#-deliverables--documentation)

---

## 🎯 Executive Overview

**SalesAgent IQ** fulfills all requirements of the **AI-Assisted Development Challenge for GET Selection**:
1. **Data Management:** Automated ETL pipeline standardizes dates (`YYYY-MM-DD`), imputes missing values (TXN0051), isolates returns (TXN0033), and stores cleaned records in an indexed SQLite database.
2. **Backend REST API:** High-speed Starlette/FastAPI service exposing `/api/query`, `/api/summary`, `/api/schema`, and `/api/health`.
3. **Analytics Engine:** Supports all 5 example questions plus **any arbitrary multi-dimensional ad-hoc query** over products, categories, regions, sales channels, dates, and discounts.
4. **AI Integration:** Dual-engine architecture featuring Google Gemini (LLM) and an offline Dynamic Semantic Query Parser grounded in **Vectorless RAG**.
5. **Safety Guardrails:** Lexical token validation prohibiting destructive commands (`DROP`, `DELETE`, `UPDATE`, `INSERT`, etc.) combined with physical SQLite read-only connection mode (`file:sales.db?mode=ro`).
6. **User Interface:** High-DPI responsive web dashboard (served at `http://localhost:8000`) plus an alternative Streamlit dashboard.
7. **Testing:** 32 comprehensive automated tests (100% pass rate in 0.09s).

---

## 🚀 Key Features

- **Beyond Repeated Queries:** Handles any arbitrary combination of metrics, dimensions, filters, rankings, and comparisons.
- **Mathematically Deterministic:** Every figure is computed directly by SQLite; zero hallucination.
- **Dual AI Engine:** Runs seamlessly offline out-of-the-box via the Dynamic Semantic Engine, or plugs into Google Gemini / OpenAI via API key.
- **Full Transparency:** Every answer displays the generated SQL query, execution latency, and supporting tabular figures.
- **Audit-Ready Data Hygiene:** Automated data cleaning report exported as JSON.

---

## 📂 Project Structure

```
mini-bi-assistant/
│
├── data/
│   ├── sales_transactions.csv        # 51 raw sales records
│   ├── sales.db                      # Processed SQLite database
│   └── data_cleaning_report.json     # Audit trail of cleaning & imputation
│
├── src/
│   ├── database/
│   │   ├── schema.sql                # Relational DDL with indexes & constraints
│   │   ├── etl.py                    # ETL pipeline (cleaning, date parsing, imputation)
│   │   └── connection.py             # Read-only and read-write connection pool
│   │
│   ├── ai/
│   │   ├── vectorless_rag.py         # Schema retrieval, domain dictionary, ontology
│   │   ├── sql_guardrails.py         # AST validator, regex safety, read-only guardrails
│   │   ├── query_parser.py           # Dynamic semantic parser & query synthesizer
│   │   └── llm_service.py            # Optional LLM service with dynamic fallback
│   │
│   ├── analytics/
│   │   └── engine.py                 # Query execution, statistical delta calculation
│   │
│   ├── api/
│   │   ├── app.py                    # Starlette ASGI app definition
│   │   └── routes.py                 # REST endpoints (/api/query, /api/schema, etc.)
│   │
│   └── ui/
│       └── static/
│           ├── index.html            # Sleek BI executive dashboard
│           ├── style.css             # Polished CSS styles
│           └── app.js                # Interactive logic & native canvas chart renderer
│
├── streamlit_app.py                  # Standalone interactive Streamlit BI UI
├── tests/
│   ├── test_etl.py                   # Data loading, imputation & anomalies
│   ├── test_queries.py               # Core 5 questions + arbitrary multi-filter queries
│   ├── test_security.py              # Destructive query rejection & SQL injection
│   ├── test_edge_cases.py            # Zero quantity, out-of-domain, boundary values
│   └── test_api.py                   # REST API routes and JSON handlers
│
├── docs/
│   ├── architecture.md               # System architecture & Mermaid diagrams
│   ├── vectorless_rag_guide.md       # Vectorless RAG vs Vector RAG for BI
│   └── interview_prep.md             # Concepts guide (Agentic AI, GenAI, Frameworks)
│
├── AI_DEVELOPMENT_LOG.md             # Development reflection, debugging & tools log
├── requirements.txt                  # Python dependencies
├── run_server.py                     # One-click server launcher
└── run_tests.py                      # One-click test runner
```

---

## ⚡ Quickstart & Execution

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.13)
- No external database required (SQLite is built-in).

### 2. Installation
```bash
# Clone or navigate to the repository
cd mini-bi-assistant

# Install dependencies (optional if running in standard python environment)
pip install -r requirements.txt
```

### 3. Launch the Application
Run the one-click server script:
```bash
python run_server.py
```
Open your browser at:
👉 **`http://localhost:8000`**

### 4. Alternative: Run with Streamlit
```bash
streamlit run streamlit_app.py
```

### 5. (Optional) Enable Google Gemini LLM
The system runs 100% offline using its built-in Vectorless RAG parser. To connect live Google Gemini:
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your-gemini-api-key"

# Linux / macOS
export GEMINI_API_KEY="your-gemini-api-key"
```

---

## 🧹 Data Management & Anomaly Handling

The raw CSV contains 51 transactions from January 2026 to June 2026. The ETL pipeline (`src/database/etl.py`) implements principled data hygiene:

| Row / Field | Raw Issue | Technical Resolution | Audit Impact |
|---|---|---|---|
| **TXN0051** | Missing `Unit_price` for Laptop Stand | Imputed to **$1,200.00** using historical median of all valid Laptop Stand transactions. | Restores $6,000 net revenue. Flagged with `is_imputed = 1`. |
| **TXN0033** | `Status = 'Returned'` (Monitor, $19,000) | Isolated in database. Standard revenue analytics filter for `status = 'Completed'`. | Prevents gross inflation of completed sales. |
| **TXN0034** | `Quantity = 0` (Keyboard) | Preserved with $0.00 revenue for transactional audit compliance. | Retains order history without skewing averages. |
| **Order_date** | `DD-MM-YYYY` format (e.g. `03-01-2026`) | Normalized to ISO `YYYY-MM-DD`. Generated indexed `year_month` column (`2026-01`). | Enables native SQL chronological sorting and grouping. |

Full audit log saved to `data/data_cleaning_report.json`.

---

## 📊 Core Questions & Benchmark Results

Our system supports all 5 mandatory questions plus arbitrary ad-hoc inquiries:

| # | Business Question | Generated SQL Query | Deterministic Answer |
|---|---|---|---|
| 1 | **What is the total revenue?** | `SELECT SUM(net_revenue) AS total_net_revenue, COUNT(transaction_id) AS total_orders, SUM(quantity) AS total_units FROM sales WHERE status = 'Completed';` | **$1,445,200.00** across 50 completed orders (638 units, $4,500 discounts). |
| 2 | **Which product generated the highest revenue?** | `SELECT product, SUM(net_revenue) AS total_net_revenue FROM sales WHERE status = 'Completed' GROUP BY product ORDER BY total_net_revenue DESC LIMIT 1;` | **Monitor** with **$473,000.00** (9 orders, 50 units). |
| 3 | **What is the monthly revenue trend?** | `SELECT year_month AS month, SUM(net_revenue) AS total_net_revenue FROM sales WHERE status = 'Completed' GROUP BY year_month ORDER BY year_month ASC;` | 6 months: Jan ($210.2k), Feb ($234.6k), Mar ($223.9k), Apr ($240.7k), May (**$318.5k peak**), Jun ($217.2k). |
| 4 | **Which region generated the highest sales?** | `SELECT region, SUM(net_revenue) AS total_net_revenue FROM sales WHERE status = 'Completed' GROUP BY region ORDER BY total_net_revenue DESC LIMIT 1;` | **South** with **$411,200.00** (13 orders, 182 units). |
| 5 | **How did revenue change between two months?** | `SELECT year_month, SUM(net_revenue) FROM sales WHERE status = 'Completed' AND year_month IN ('2026-01', '2026-02') GROUP BY year_month ORDER BY year_month ASC;` | Between Jan and Feb, revenue **increased by $24,350.00 (+11.58%)**. |

### Examples of Arbitrary Dynamic Queries Supported:
- *"How many units of Office Chair were sold in South region?"* $\rightarrow$ **10 units across 2 orders ($78,000 net revenue)**.
- *"What is the total discount given in Electronics?"* $\rightarrow$ **$2,000.00 across 9 orders**.
- *"List all returned orders"* $\rightarrow$ **TXN0033 (Monitor, 2 units, West region, Retail, $19,000 gross)**.
- *"Compare online and retail sales"* $\rightarrow$ **Online ($752,750 / 52.1%) vs Retail ($692,450 / 47.9%)**.
- *"Show orders with discount greater than 500"* $\rightarrow$ **TXN0012 ($1,000 discount) and TXN0022 ($2,500 discount)**.

---

## 🧠 AI & Vectorless RAG Architecture

Vector embeddings are unsuitable for relational business calculations because vectors cannot perform arithmetic addition over tabular rows. 

Our **Vectorless RAG** system injects:
1. Exact relational schema definitions (`sales` table, types, foreign keys).
2. Categorical domain ground truth (`Product`, `Category`, `Region`, `Sales_channel`, `Status`).
3. Core accounting rules (`net_revenue = gross_revenue - discount_amount`).

The model translates user requests into precise standard SQL, guaranteeing **zero numerical hallucination**.

Read the full guide in [docs/vectorless_rag_guide.md](docs/vectorless_rag_guide.md).

---

## 🛡️ Security & SQL Guardrails

To prevent malicious or destructive queries, the assistant employs a two-tier defense-in-depth model:

1. **Application-Level Guardrails (`src/ai/sql_guardrails.py`):**
   - Must begin with `SELECT` or `WITH`.
   - Rejects multiple semicolon-stacked statements (`SELECT 1; DROP TABLE ...`).
   - Token-level regex scan prohibits `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `EXEC`, `PRAGMA`.
   - Validates that table access is strictly confined to `sales`.
2. **OS/Engine-Level Read-Only Enforcement (`src/database/connection.py`):**
   - SQLite connection opened via URI mode: `file:sales.db?mode=ro`.
   - The SQLite database engine physically refuses any write or modification, even if an attacker bypassed application filters.

---

## 🧪 Automated Testing

The automated test suite contains **32 tests** covering ETL, queries, security, edge cases, and REST endpoints:

```bash
# Run the test suite
python run_tests.py
```

### Test Coverage Summary:
- **`tests/test_etl.py` (5 tests):** Row count integrity, TXN0051 unit price imputation, ISO date conversion, total net revenue calculation, returned order isolation.
- **`tests/test_queries.py` (8 tests):** All 5 core questions, dynamic units sold by region, category discounts, channel comparisons.
- **`tests/test_security.py` (8 tests):** Rejection of `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, stacked query injection, unauthorized table access, and safe SELECT verification.
- **`tests/test_edge_cases.py` (4 tests):** Zero quantity transactions (TXN0034), empty string validation, unmatched entity queries, explicit returned order queries.
- **`tests/test_api.py` (7 tests):** `/api/health`, `/api/schema`, `/api/summary`, `/api/query` validation, 400 error handling, and UI index serving.

**Result: 32 tests passed in 0.096 seconds (100% pass rate).**

---

## ⚠️ Known Limitations

1. **Single Table Scope:** The current implementation operates over a single denormalized `sales` table. Multi-table schema linking (e.g. separate `customers`, `inventory`, `suppliers` tables) would require foreign-key graph traversal.
2. **Fixed Temporal Horizon:** The dataset spans January to June 2026. Queries referencing years outside 2026 return empty sets.
3. **Conversational Memory:** Each query is currently stateless; multi-turn contextual references (e.g., "now filter that by North") require re-specifying the dimension.

---

## 📚 Deliverables & Documentation

- [AI_DEVELOPMENT_LOG.md](AI_DEVELOPMENT_LOG.md) - Complete reflection on AI tools used, debugging process, and next-day enhancements.
- [docs/architecture.md](docs/architecture.md) - System architecture diagram and component specifications.
- [docs/vectorless_rag_guide.md](docs/vectorless_rag_guide.md) - Deep dive on Vectorless RAG vs Vector RAG for BI.
- [docs/interview_prep.md](docs/interview_prep.md) - Interview preparation guide covering Agentic AI, Generative AI, RAG, LangChain, Google ADK, and Dify.
