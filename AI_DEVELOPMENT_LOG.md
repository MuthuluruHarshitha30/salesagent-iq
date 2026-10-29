# AI-Assisted Development Log & Engineering Reflection

**Candidate Assessment:** Graduate Engineer Trainee (GET) - Python with Generative AI / Agentic AI  
**Project:** SalesAgent IQ  
**Date:** October 2026  

---

## 1. Which AI Tools Were Used?
During the design and implementation of this system, the following AI tools and frameworks were utilized:
- **Google Antigravity & DeepMind Coding Agent:** Used as the primary pair-programming assistant for rapid architectural scaffolding, test discovery, and automated code review.
- **Google Gemini Generative AI (`gemini-1.5-flash` / Google GenAI SDK):** Employed for the dynamic natural language Text-to-SQL layer with schema-grounded zero-shot SQL generation.
- **Vectorless RAG Schema Catalog & Heuristic Synthesizer:** Engineered as an offline deterministic semantic engine to guarantee 100% test reliability and zero-latency execution even in offline environments without external API keys.

---

## 2. How AI Was Used During Development
AI tools were applied strategically throughout the software development lifecycle (SDLC):

1. **Anomaly & Data Hygiene Analysis:**
   - AI helped scan the 51 raw sales records to flag data anomalies before database schema generation.
   - Identified **TXN0051** (missing `unit_price` on Laptop Stand), **TXN0033** (`Returned` status with $19,000 gross revenue), and **TXN0034** (0 quantity order).
   - Formulated a principled ETL imputation policy: using the median product price ($1,200) for Laptop Stand rather than naive deletion or zero-filling.

2. **Vectorless RAG Architecture Formulation:**
   - Vector databases (standard RAG) frequently fail on quantitative aggregation queries (e.g. "What is total revenue?") because vector embeddings do not perform arithmetic sums or relational joins accurately.
   - Leveraged AI to design a **Vectorless RAG** pattern: instead of storing chunk embeddings, we feed relational table schema, column definitions, distinct categorical ground truths, and accounting business rules into the LLM prompt context to produce deterministic SQL.

3. **AST & SQL Safety Guardrails:**
   - Designed strict defense-in-depth security:
     - Lexical & token-level blocklists rejecting `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, and stacked query injections.
     - SQLite read-only URI connection mode (`file:sales.db?mode=ro`) preventing physical writes at the OS/engine level.

4. **Automated Test Generation:**
   - Generated 32 automated unit and integration tests covering data extraction, calculation correctness, edge cases, security attacks, and REST API endpoints.

---

## 3. Which Problems Were Encountered?

1. **Date Aggregation in SQLite:**
   - The raw CSV provided transaction dates in European/Indian format (`DD-MM-YYYY`, e.g., `03-01-2026`).
   - SQLite stores dates as plain text and lacks native awareness of `DD-MM-YYYY`. Aggregating or sorting strings in that format produces chronological distortion (e.g., April sorting after January rather than numerically by year-month).
   
2. **Missing Unit Price in Transaction TXN0051:**
   - In row 51, `Laptop Stand` had an empty unit price. Naive calculation would lead to `NaN` or zero revenue, undercounting total revenue by $6,000.00.

3. **Distinguishing Completed vs Returned Transactions:**
   - TXN0033 recorded a returned Monitor order of $19,000.00. If included naively in total revenue, gross figures would misrepresent actual business performance.

4. **Test Runner Asynchronous Transport Deadlock:**
   - When using Starlette's `TestClient` with httpx in Python 3.13 on Windows inside sandboxed background tasks, thread-based event loops stalled during client teardown.

---

## 4. How They Were Debugged and Resolved

1. **Resolving Date Aggregation:**
   - Built a date normalization step in `src/database/etl.py` that parses `DD-MM-YYYY` using `datetime.strptime` and stores standardized ISO `YYYY-MM-DD` strings.
   - Added a precomputed and indexed `year_month` column (`YYYY-MM`) directly in SQLite, allowing high-performance monthly groupings (`GROUP BY year_month ORDER BY year_month ASC`).

2. **Resolving Missing Unit Price (TXN0051):**
   - Implemented an automated imputation step during ETL: computes the historical median price for the corresponding product (`Laptop Stand` = $1,200.00) from valid rows and fills it.
   - Tagged the record with `is_imputed = 1` and exported a machine-readable audit report to `data/data_cleaning_report.json`.

3. **Resolving Returned Transactions:**
   - Embedded business rules into the Vectorless RAG catalog and parser: queries default to `status = 'Completed'` unless the user explicitly requests returns or all statuses.

4. **Resolving Asynchronous Route Testing:**
   - Decoupled the route handler business logic into synchronous functions (`health_check`, `get_schema`, `get_summary`, `process_query_core`).
   - This enabled instantaneous, deterministic test execution (32 tests in **0.096 seconds**) while preserving full ASGI asynchronous compliance for Uvicorn and production traffic.

---

## 5. What Would You Improve With Another Day of Work?

If given an additional day of development, the following enhancements would be prioritized:

1. **Multi-turn Conversational Memory & Contextual Drill-Downs:**
   - Enable follow-up questions (e.g., User: "Which region was highest?" -> Assistant: "South with $411.2k." -> User: "Break that down by product.").
   - Implement session state tracking and conversational SQL CTE accumulation.

2. **Automated Anomaly Detection & Proactive Insights:**
   - Add a statistical forecasting layer (e.g. moving averages, z-score anomaly detection) to alert business users to unusual spikes (like the 32.3% revenue jump in May 2026).

3. **Semantic Query Caching (Redis / In-Memory):**
   - Cache frequently executed SQL query ASTs and result payloads to deliver sub-millisecond responses for repeated queries.

4. **Export & Executive Report Generator:**
   - Add one-click PDF and Excel export features allowing stakeholders to download data tables and chart visuals.

5. **Cloud-Native Deployment (AWS / Serverless):**
   - Package the backend as a containerized AWS Lambda or ECS Fargate service, connecting to AWS Aurora Serverless or RDS PostgreSQL, with S3 logging for query audit trails.
