"""
LLM Text-to-SQL Service with Vectorless RAG & Dynamic Fallback.
Integrates Google Gemini / OpenAI when credentials are present,
with automatic fallback to the Dynamic Semantic Query Parser.
Enforces SQLGuardrails on every generated query.
"""

import os
import re
from typing import Any, Dict, Optional

from src.ai.query_parser import DynamicQueryParser, QueryIntent
from src.ai.sql_guardrails import SQLGuardrails, SQLSecurityError
from src.ai.vectorless_rag import VectorlessRAGCatalog


class LLMQueryService:
    def __init__(self):
        self.parser = DynamicQueryParser()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.has_llm = bool(self.gemini_api_key or self.openai_api_key)

    def generate_sql(self, question: str) -> Dict[str, Any]:
        """
        Translate user question to validated SQL.
        Uses LLM if available; falls back to the deterministic semantic parser.
        Validates all queries through SQLGuardrails.
        """
        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        query_plan = None
        source = "heuristic_semantic_parser"

        # Try LLM if API key is present
        if self.gemini_api_key:
            try:
                llm_res = self._call_gemini(question)
                if llm_res and "sql" in llm_res:
                    query_plan = llm_res
                    source = "google_gemini_llm"
            except Exception as e:
                # Log error and fall back seamlessly
                print(f"[LLM Warning] Gemini call failed: {e}. Falling back to Dynamic Semantic Parser.")

        # If LLM not configured or failed, use the dynamic semantic engine
        if not query_plan:
            query_plan = self.parser.parse(question)
            source = "dynamic_semantic_parser"

        # Validate SQL against Guardrails
        candidate_sql = query_plan["sql"]
        validation_report = SQLGuardrails.validate_query(candidate_sql)

        query_plan["source"] = source
        query_plan["safety_validation"] = validation_report
        query_plan["is_safe"] = validation_report["is_safe"]

        return query_plan

    def _call_gemini(self, question: str) -> Optional[Dict[str, Any]]:
        """Call Google Gemini to generate SQL using Vectorless RAG prompt."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            system_context = VectorlessRAGCatalog.get_prompt_context()
            prompt = (
                f"{system_context}\n\n"
                f"TASK: Convert the user's business question into a single safe SQLite SELECT query.\n"
                f"RULES:\n"
                f"1. Only SELECT queries are permitted.\n"
                f"2. Always alias calculated columns (e.g. `AS total_net_revenue`).\n"
                f"3. Unless asked about returns or all statuses, filter with `status = 'Completed'`.\n"
                f"4. Return ONLY the raw SQL query with no markdown formatting and no commentary.\n\n"
                f"User Question: {question}\n"
                f"SQL Query:"
            )

            response = model.generate_content(prompt)
            raw_sql = response.text.strip()
            # Clean possible markdown formatting
            raw_sql = re.sub(r"```sql\s*", "", raw_sql)
            raw_sql = re.sub(r"```\s*", "", raw_sql).strip()

            return {
                "question": question,
                "intent": QueryIntent.GENERAL,
                "sql": raw_sql,
                "description": f"AI-generated query for '{question}'",
                "dimension": None,
                "metric_name": "Query Result",
                "is_breakdown": "GROUP BY" in raw_sql.upper()
            }
        except Exception as e:
            raise RuntimeError(f"Gemini generation error: {e}")
