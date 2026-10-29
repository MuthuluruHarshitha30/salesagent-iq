# GET Technical Interview Preparation Guide

**Assessment:** Graduate Engineer Trainee (GET) - Python with Generative AI / Agentic AI  
**Role Scope:** Generative AI, Agentic AI, RAG, Vectorless RAG, Agentic Frameworks (LangChain, Google ADK, Dify), AWS AI/ML services.

---

## 1. Core Concepts

### A. Generative AI vs Agentic AI
- **Generative AI (GenAI):**
  - Focuses on content creation (text, code, images) based on input prompts.
  - Typically single-turn, stateless, and passive: input prompt $\rightarrow$ output generation.
  - Lacks agency, autonomous goal pursuit, environment interaction, or self-correction.
- **Agentic AI:**
  - Autonomous systems capable of multi-step reasoning, planning, tool usage, environment observation, and recursive goal execution.
  - Operates via the **Perception-Reasoning-Action-Reflection (ReAct)** loop.
  - Can call external APIs, query databases, execute code, observe results, adjust strategy upon failure, and deliver complex outcomes without constant human prompting.

### B. RAG (Retrieval-Augmented Generation) vs Vectorless RAG
- **Standard RAG (Vector RAG):**
  - Chunks text into passages, generates vector embeddings, stores them in vector databases (Pinecone, Chroma, Qdrant), and retrieves chunks via cosine similarity.
  - Ideal for: Unstructured knowledge bases, support tickets, policy manuals.
  - Major Weakness: Cannot calculate exact sums, averages, or counts across tabular rows.
- **Vectorless RAG:**
  - Retrieves relational schemas, column metadata, entity catalogs, and business calculation logic without using embedding vectors.
  - Generates deterministic SQL queries executed against relational database engines (PostgreSQL, SQLite, BigQuery, Snowflake).
  - Guarantees 100% numerical accuracy and zero hallucination on quantitative aggregations.

---

## 2. Agentic Frameworks: Deep Dive

### A. LangChain / LangGraph
- **LangChain:**
  - Foundational Python framework for composing LLM applications using Chains, Prompts, Tools, and OutputParsers.
- **LangGraph:**
  - Extension of LangChain using state machine graphs (nodes, edges, conditional branching) to build cyclical, multi-agent workflows with human-in-the-loop approvals, persistent checkpointing, and branch rollback.

### B. Google ADK (Agent Development Kit) & Vertex AI
- **Google ADK / Vertex AI Agent Builder:**
  - Enterprise framework by Google Cloud for orchestrating goal-directed agents powered by Gemini models.
  - Natively integrates Grounding with Google Search, enterprise datastores, and tool calling with OpenAPI specs.
  - Employs constitutional AI guardrails and safety filters built into Vertex AI.

### C. Dify
- **Dify (`dify.ai`):**
  - Modern open-source visual workflow engine and LLMOps platform for building AI applications, RAG pipelines, and autonomous agents.
  - Features visual node-based workflow orchestration (LLM nodes, Code nodes, Knowledge Retrieval nodes, Tool nodes, Condition branches).
  - Offers built-in vector database management, hybrid search (keyword + vector), prompt engineering sandboxes, and API generation.

---

## 3. How This Project Implements These Concepts

1. **Agentic Pattern in this Assistant:**
   - **User Intent Classification:** Analyzes user query to recognize intent (Aggregation, Breakdown, Ranking, Comparison, Record Lookup).
   - **Schema Linking:** Deterministically matches extracted entities to real database columns and categorical values.
   - **Tool Execution:** Executes validated SQL against the database engine via a strictly read-only connection.
   - **Self-Correction & Reflection:** Catches database errors or empty sets, dynamically returning helpful guidance.
2. **Safety & Guardrails:**
   - Enforces strict read-only execution at both the application level (AST token check) and database connection level (SQLite URI `mode=ro`).
3. **Data Cleansing & Ingestion Audit:**
   - Demonstrates production ETL best practices: automated missing value imputation (TXN0051), anomaly isolation (TXN0033 returned order), and ISO temporal standardization.
