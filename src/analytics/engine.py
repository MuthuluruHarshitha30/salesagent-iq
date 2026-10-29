"""
Analytics Execution Engine.
Executes validated queries against the read-only database,
computes supporting statistical figures, calculates comparative deltas,
and formats human-readable natural language answers.
"""

import time
from typing import Any, Dict, List, Optional, Tuple
from src.ai.llm_service import LLMQueryService
from src.ai.query_parser import QueryIntent
from src.database.connection import get_ro_connection


class AnalyticsEngine:
    def __init__(self):
        self.ai_service = LLMQueryService()

    def process_question(self, question: str) -> Dict[str, Any]:
        """
        End-to-end question processing pipeline:
        Natural language -> AI/Vectorless RAG -> SQL Guardrails -> DB Execution -> Analysis & Formatting
        """
        start_time = time.perf_counter()

        # 1. Translate question to validated SQL plan
        query_plan = self.ai_service.generate_sql(question)
        sql = query_plan["sql"]

        # 2. Execute SQL against Read-Only SQLite database
        conn = get_ro_connection()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        records = [dict(zip(col_names, row)) for row in rows]
        exec_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 3. Generate natural language response and analytical insights
        summary_text, chart_data, comparative_metrics = self._synthesize_answer(
            question=question,
            plan=query_plan,
            records=records,
            col_names=col_names
        )

        return {
            "question": question,
            "intent": query_plan["intent"],
            "description": query_plan.get("description", ""),
            "sql_query": sql,
            "execution_time_ms": exec_duration_ms,
            "ai_source": query_plan.get("source", "dynamic_semantic_parser"),
            "safety_validation": query_plan.get("safety_validation", {}),
            "summary": summary_text,
            "columns": col_names,
            "supporting_data": records,
            "row_count": len(records),
            "chart_data": chart_data,
            "comparative_metrics": comparative_metrics,
            "applied_filters": query_plan.get("applied_filters", [])
        }

    def _synthesize_answer(
        self,
        question: str,
        plan: Dict[str, Any],
        records: List[Dict[str, Any]],
        col_names: List[str]
    ) -> Tuple[str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Generate human-friendly narrative, chart payload, and delta statistics."""
        intent = plan.get("intent")
        comp_metrics = None
        chart_data = None

        if not records:
            return (
                "No matching sales records were found in the database for the given criteria.",
                None,
                None
            )

        # 1. TOTAL AGGREGATION INTENT
        if intent == QueryIntent.TOTAL_METRIC:
            row = records[0]
            # Primary metric column (first column)
            metric_col = col_names[0]
            val = row[metric_col]

            if val is None or row.get("total_orders", 0) == 0:
                return (
                    "No matching sales records were found in the database for the given criteria.",
                    None,
                    None
                )

            metric_label = plan.get("metric_name", metric_col.replace("_", " ").title())

            if isinstance(val, (int, float)):
                val_formatted = f"${val:,.2f}" if "revenue" in metric_col or "discount" in metric_col or "price" in metric_col else f"{val:,}"
            else:
                val_formatted = str(val)

            summary = f"The {metric_label.lower()} is {val_formatted} across {row.get('total_orders', 'all')} completed transactions."
            
            # Supporting breakdown
            extra_bits = []
            if "total_orders" in row and row["total_orders"] is not None:
                extra_bits.append(f"{row['total_orders']} orders")
            if "total_units" in row and row["total_units"] is not None:
                extra_bits.append(f"{row['total_units']} total units sold")
            if "total_discounts" in row and row["total_discounts"] is not None and row["total_discounts"] > 0:
                extra_bits.append(f"${row['total_discounts']:,.2f} discounts applied")
            if extra_bits:
                summary += f" (Supporting figures: {', '.join(extra_bits)})."

            chart_data = {
                "type": "kpi",
                "label": metric_label,
                "value": val_formatted,
                "raw_value": val,
                "subtext": f"{row.get('total_orders', 0)} completed orders"
            }
            return summary, chart_data, None

        # 2. COMPARISON INTENT
        elif intent == QueryIntent.COMPARISON:
            comp_info = plan.get("comparison_info", {})
            dim = plan.get("dimension", "period")

            if len(records) >= 2:
                r1 = records[0]
                r2 = records[1]
                e1_label = r1.get(dim)
                e2_label = r2.get(dim)
                v1 = r1.get("total_net_revenue", 0.0)
                v2 = r2.get("total_net_revenue", 0.0)

                diff = round(v2 - v1, 2)
                pct_change = round((diff / v1) * 100, 2) if v1 else 0.0
                direction = "increased" if diff >= 0 else "decreased"

                comp_metrics = {
                    "entity1": {"name": e1_label, "revenue": v1, "orders": r1.get("total_orders"), "units": r1.get("total_units")},
                    "entity2": {"name": e2_label, "revenue": v2, "orders": r2.get("total_orders"), "units": r2.get("total_units")},
                    "absolute_difference": diff,
                    "percentage_change": pct_change,
                    "direction": direction
                }

                summary = (
                    f"Between {e1_label} and {e2_label}, revenue {direction} by ${abs(diff):,.2f} "
                    f"({abs(pct_change):.2f}%). Revenue was ${v1:,.2f} in {e1_label} and ${v2:,.2f} in {e2_label}."
                )

                chart_data = {
                    "type": "bar",
                    "labels": [str(e1_label), str(e2_label)],
                    "values": [v1, v2],
                    "title": f"Revenue Comparison: {e1_label} vs {e2_label}"
                }
                return summary, chart_data, comp_metrics
            else:
                return f"Comparison data returned {len(records)} record(s).", None, None

        # 3. BREAKDOWN OR RANKING INTENT
        elif intent in (QueryIntent.BREAKDOWN, QueryIntent.RANKING):
            dim_col = col_names[0]
            metric_col = col_names[1]

            top_item = records[0]
            top_name = top_item.get(dim_col)
            top_val = top_item.get(metric_col)
            metric_label = plan.get("metric_name", metric_col.replace("_", " ").title())

            if isinstance(top_val, (int, float)):
                top_formatted = f"${top_val:,.2f}" if "revenue" in metric_col or "discount" in metric_col or "price" in metric_col else f"{top_val:,}"
            else:
                top_formatted = str(top_val)

            # Monthly trend special handling
            if dim_col in ("year_month", "month"):
                peak_record = max(records, key=lambda r: r.get(metric_col, 0))
                peak_month = peak_record.get(dim_col)
                peak_val = peak_record.get(metric_col, 0)
                peak_formatted = f"${peak_val:,.2f}" if "revenue" in metric_col else f"{peak_val:,}"

                summary = (
                    f"Monthly revenue trend across {len(records)} months. "
                    f"Peak month was {peak_month} with {peak_formatted} in revenue."
                )
                chart_data = {
                    "type": "line",
                    "labels": [str(r[dim_col]) for r in records],
                    "values": [r[metric_col] for r in records],
                    "title": "Monthly Revenue Trend"
                }
            else:
                summary = (
                    f"The top-performing {dim_col} is '{top_name}' with {top_formatted} in {metric_label.lower()} "
                    f"({top_item.get('total_orders', 0)} orders, {top_item.get('total_units', 0)} units)."
                )
                chart_data = {
                    "type": "bar",
                    "labels": [str(r[dim_col]) for r in records[:10]],
                    "values": [r[metric_col] for r in records[:10]],
                    "title": f"{metric_label} by {dim_col.title()}"
                }

            return summary, chart_data, None

        # 4. RECORD LOOKUP INTENT
        elif intent == QueryIntent.RECORD_LOOKUP:
            summary = f"Retrieved {len(records)} transaction record(s) matching your request."
            return summary, None, None

        # 5. ENTITY LIST INTENT (e.g., "what are the different products", "list all categories")
        elif intent == QueryIntent.ENTITY_LIST:
            dim_col = plan.get("dimension", col_names[0])
            entity_label = plan.get("entity_info", {}).get("label", dim_col.title())
            distinct_items = [str(r[dim_col]) for r in records if dim_col in r]

            if len(distinct_items) > 2:
                items_str = ", ".join(distinct_items[:-1]) + f", and {distinct_items[-1]}"
            elif len(distinct_items) == 2:
                items_str = f"{distinct_items[0]} and {distinct_items[1]}"
            else:
                items_str = distinct_items[0] if distinct_items else "None"

            summary = f"There are {len(distinct_items)} distinct {entity_label.lower()} in the sales dataset: {items_str}."

            chart_data = {
                "type": "bar",
                "labels": [str(r[dim_col]) for r in records],
                "values": [r.get("total_net_revenue", r.get("total_orders", 0)) for r in records],
                "title": f"Net Revenue by {entity_label}"
            }
            return summary, chart_data, None

        # Default fallback
        first_row = records[0]
        summary = f"Query executed successfully, returning {len(records)} result(s)."
        return summary, None, None
