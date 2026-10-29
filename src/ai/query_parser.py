"""
Dynamic Semantic Query Parser & Intent Engine (Vectorless RAG).
Translates arbitrary natural language business questions into precise,
safe SQLite queries over the sales transactions dataset.
Supports multi-dimensional filtering, arbitrary metrics, comparative analytics,
rankings, breakdowns, and ad-hoc aggregations.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from src.ai.vectorless_rag import VectorlessRAGCatalog


class QueryIntent:
    TOTAL_METRIC = "TOTAL_METRIC"
    BREAKDOWN = "BREAKDOWN"
    RANKING = "RANKING"
    COMPARISON = "COMPARISON"
    RECORD_LOOKUP = "RECORD_LOOKUP"
    ENTITY_LIST = "ENTITY_LIST"
    RAW_QUERY = "RAW_QUERY"
    GENERAL = "GENERAL"


class DynamicQueryParser:
    """
    Parses arbitrary natural language queries into safe SQL using domain ontology,
    entity extraction, metric mapping, dimension resolution, and filter composition.
    """

    PRODUCT_SYNONYMS = {
        "laptop stand": "Laptop Stand",
        "stand": "Laptop Stand",
        "laptop": "Laptop Stand",
        "wireless mouse": "Wireless Mouse",
        "mouse": "Wireless Mouse",
        "office chair": "Office Chair",
        "chair": "Office Chair",
        "chairs": "Office Chair",
        "monitor": "Monitor",
        "monitors": "Monitor",
        "screen": "Monitor",
        "keyboard": "Keyboard",
        "keyboards": "Keyboard",
        "desk": "Desk",
        "desks": "Desk",
        "table": "Desk",
        "usb-c hub": "USB-C Hub",
        "usb c hub": "USB-C Hub",
        "usb hub": "USB-C Hub",
        "hub": "USB-C Hub"
    }

    CATEGORY_SYNONYMS = {
        "accessories": "Accessories",
        "accessory": "Accessories",
        "furniture": "Furniture",
        "furnitures": "Furniture",
        "electronics": "Electronics",
        "electronic": "Electronics"
    }

    REGION_SYNONYMS = {
        "north": "North",
        "northern": "North",
        "south": "South",
        "southern": "South",
        "east": "East",
        "eastern": "East",
        "west": "West",
        "western": "West"
    }

    CHANNEL_SYNONYMS = {
        "online": "Online",
        "web": "Online",
        "internet": "Online",
        "e-commerce": "Online",
        "ecommerce": "Online",
        "retail": "Retail",
        "store": "Retail",
        "offline": "Retail",
        "physical": "Retail"
    }

    MONTH_LOOKUP = VectorlessRAGCatalog.MONTH_MAP

    MONTH_NAMES = {
        "2026-01": "January 2026",
        "2026-02": "February 2026",
        "2026-03": "March 2026",
        "2026-04": "April 2026",
        "2026-05": "May 2026",
        "2026-06": "June 2026"
    }

    def parse(self, question: str) -> Dict[str, Any]:
        """
        Analyze arbitrary natural language question and construct the corresponding
        deterministic SQL query and metadata.
        """
        if not question or not question.strip():
            raise ValueError("Query string cannot be empty.")

        q_clean = question.strip()
        q_lower = q_clean.lower()

        # 1. Extract entities and filters
        filters, filter_desc = self._extract_filters(q_lower)
        
        # 2. Extract comparison intent (e.g. between two months or two entities)
        comparison_info = self._check_comparison(q_lower)
        if comparison_info:
            return self._build_comparison_query(q_clean, comparison_info, filters)

        # 3. Check for distinct entity listing intent (e.g., "what are the different products")
        entity_list_info = self._check_entity_listing(q_lower, filters)
        if entity_list_info:
            return self._build_entity_list_query(q_clean, entity_list_info, filters)

        # 4. Check for specific transaction ID lookup (e.g., TXN0004)
        txn_match = re.search(r"\b(TXN\d{4})\b", q_clean, re.IGNORECASE)
        if txn_match:
            txn_id = txn_match.group(1).upper()
            sql = f"SELECT transaction_id, order_date, product, category, region, sales_channel, quantity, unit_price, discount_amount, gross_revenue, net_revenue, status, is_imputed FROM sales WHERE transaction_id = '{txn_id}';"
            return {
                "question": q_clean,
                "intent": QueryIntent.RECORD_LOOKUP,
                "sql": sql,
                "description": f"Lookup details for transaction {txn_id}",
                "metric_name": "Transaction Details",
                "is_breakdown": False
            }

        # 4. Check for record listings (e.g. "show all returned orders", "orders with discount > 500")
        if any(term in q_lower for term in ["list all", "show all", "view all", "list of", "show orders", "show transactions", "list transactions", "returned orders"]):
            return self._build_record_list_query(q_clean, q_lower, filters)

        # 5. Extract metric (Revenue, Gross Revenue, Discount, Quantity, Price, AOV, Orders)
        metric_expr, metric_alias, metric_name = self._resolve_metric(q_lower)

        # 6. Extract dimension for breakdown / grouping
        dimension, dim_alias = self._resolve_dimension(q_lower)

        # 7. Check for ranking intent (highest, lowest, top N)
        ranking_info = self._resolve_ranking(q_lower)

        # 8. Assemble SQL
        # Base WHERE conditions
        where_clauses = list(filters)

        # Default to completed orders unless returns or all statuses requested
        status_specified = any("status" in f.lower() for f in filters)
        if not status_specified:
            if "returned" in q_lower or "return" in q_lower:
                where_clauses.append("status = 'Returned'")
            elif "all status" in q_lower or "both completed and returned" in q_lower:
                pass  # do not filter status
            else:
                where_clauses.append("status = 'Completed'")

        where_str = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        if dimension:
            # Breakdown or Ranking Query
            order_dir = ranking_info.get("direction", "DESC")
            limit_val = ranking_info.get("limit")
            limit_str = f" LIMIT {limit_val}" if limit_val else ""

            # Check if chronological ordering is preferred for trends over time
            order_clause = f"ORDER BY {metric_alias} {order_dir}"
            if dim_alias in ("month", "year_month", "order_date") and any(w in q_lower for w in ["trend", "over time", "month-by-month", "chronological", "monthly trend"]):
                order_clause = f"ORDER BY {dimension} ASC"

            # Check if user asked "which product/region" -> usually top 1
            if ("which" in q_lower or "what" in q_lower) and ("highest" in q_lower or "top" in q_lower or "most" in q_lower or "best" in q_lower or "maximum" in q_lower):
                if not limit_val and not any(w in q_lower for w in ["trend", "all"]):
                    limit_str = " LIMIT 1"

            sql = (
                f"SELECT {dimension} AS {dim_alias}, {metric_expr} AS {metric_alias}, "
                f"COUNT(transaction_id) AS total_orders, SUM(quantity) AS total_units "
                f"FROM sales{where_str} "
                f"GROUP BY {dimension} "
                f"{order_clause}{limit_str};"
            )

            intent = QueryIntent.RANKING if (limit_str or "ORDER BY" in sql) else QueryIntent.BREAKDOWN
            return {
                "question": q_clean,
                "intent": intent,
                "sql": sql,
                "description": f"Breakdown of {metric_name} grouped by {dim_alias}",
                "dimension": dim_alias,
                "metric_name": metric_name,
                "metric_alias": metric_alias,
                "is_breakdown": True,
                "applied_filters": filter_desc
            }
        else:
            # Single Aggregation Query
            sql = (
                f"SELECT {metric_expr} AS {metric_alias}, "
                f"COUNT(transaction_id) AS total_orders, "
                f"SUM(quantity) AS total_units, "
                f"SUM(discount_amount) AS total_discounts, "
                f"ROUND(AVG(net_revenue), 2) AS avg_transaction_value "
                f"FROM sales{where_str};"
            )

            return {
                "question": q_clean,
                "intent": QueryIntent.TOTAL_METRIC,
                "sql": sql,
                "description": f"Total {metric_name} with supporting summary statistics",
                "dimension": None,
                "metric_name": metric_name,
                "metric_alias": metric_alias,
                "is_breakdown": False,
                "applied_filters": filter_desc
            }

    def _extract_filters(self, q_lower: str) -> Tuple[List[str], List[str]]:
        """Extract WHERE clause filters from natural language."""
        filters = []
        desc = []

        # 1. Product filter
        matched_prod = None
        # Match longer keys first to avoid 'mouse' before 'wireless mouse'
        sorted_prods = sorted(self.PRODUCT_SYNONYMS.keys(), key=lambda x: len(x), reverse=True)
        for key in sorted_prods:
            if re.search(r"\b" + re.escape(key) + r"\b", q_lower):
                # Only use if not asking "which product" / "by product"
                if not any(token in q_lower for token in ["by product", "which product", "per product", "top product", "each product"]):
                    matched_prod = self.PRODUCT_SYNONYMS[key]
                    break
        if matched_prod:
            filters.append(f"product = '{matched_prod}'")
            desc.append(f"Product: {matched_prod}")

        # 2. Category filter
        for key, cat in self.CATEGORY_SYNONYMS.items():
            if re.search(r"\b" + re.escape(key) + r"\b", q_lower):
                if not any(token in q_lower for token in ["by category", "which category", "per category"]):
                    filters.append(f"category = '{cat}'")
                    desc.append(f"Category: {cat}")
                    break

        # 3. Region filter
        for key, reg in self.REGION_SYNONYMS.items():
            if re.search(r"\b" + re.escape(key) + r"\b", q_lower):
                if not any(token in q_lower for token in ["by region", "which region", "per region", "top region"]):
                    filters.append(f"region = '{reg}'")
                    desc.append(f"Region: {reg}")
                    break

        # 4. Sales Channel filter
        for key, ch in self.CHANNEL_SYNONYMS.items():
            if re.search(r"\b" + re.escape(key) + r"\b", q_lower):
                if not any(token in q_lower for token in ["by channel", "sales channel", "by sales channel", "which channel"]):
                    filters.append(f"sales_channel = '{ch}'")
                    desc.append(f"Channel: {ch}")
                    break

        # 5. Month / Date filter (single month)
        # Avoid matching if asking about monthly trend or comparison between two months
        if not any(token in q_lower for token in ["monthly", "trend", "month-by-month", "between", "compare"]):
            for m_key, ym in self.MONTH_LOOKUP.items():
                if re.search(r"\b" + re.escape(m_key) + r"\b", q_lower):
                    filters.append(f"year_month = '{ym}'")
                    desc.append(f"Month: {self.MONTH_NAMES.get(ym, ym)}")
                    break

        # 6. Status filter
        if "returned" in q_lower or "returns" in q_lower:
            filters.append("status = 'Returned'")
            desc.append("Status: Returned")
        elif "completed" in q_lower:
            filters.append("status = 'Completed'")
            desc.append("Status: Completed")

        # 7. Numerical comparisons (e.g., discount > 500, quantity >= 10)
        gt_disc = re.search(r"discount\s*(?:greater than|more than|>|above)\s*(\d+)", q_lower)
        if gt_disc:
            val = gt_disc.group(1)
            filters.append(f"discount_amount > {val}")
            desc.append(f"Discount > ${val}")

        # 8. Unmatched entity fallback (e.g., "for Supercar")
        if not (matched_prod or any("category" in f for f in filters) or any("region" in f for f in filters) or any("year_month" in f for f in filters)):
            m_entity = re.search(r"\b(?:for|of)\s+([a-zA-Z0-9_\s]+?)(?:\?|$|\s+in\b|\s+with\b)", q_lower)
            if m_entity:
                cand = m_entity.group(1).strip()
                stop_words = {"all", "both", "the", "each", "total", "monthly", "completed", "returned", "every", "any", "two months", "months", "revenue", "sales"}
                if cand and cand not in stop_words and len(cand) > 2:
                    filters.append(f"product = '{cand.title()}'")
                    desc.append(f"Product: {cand.title()}")

        return filters, desc

    def _resolve_metric(self, q_lower: str) -> Tuple[str, str, str]:
        """Map text to SQL aggregation expression, column alias, and human label."""
        if any(w in q_lower for w in ["gross revenue", "gross sales"]):
            return "SUM(gross_revenue)", "total_gross_revenue", "Gross Revenue"
        elif any(w in q_lower for w in ["discount", "discounts", "discount amount"]):
            if "average discount" in q_lower or "avg discount" in q_lower:
                return "ROUND(AVG(discount_amount), 2)", "avg_discount", "Average Discount"
            return "SUM(discount_amount)", "total_discount", "Total Discount"
        elif any(w in q_lower for w in ["quantity", "units", "items sold", "volume", "units sold"]):
            if "average quantity" in q_lower or "avg units" in q_lower:
                return "ROUND(AVG(quantity), 2)", "avg_quantity", "Average Quantity"
            return "SUM(quantity)", "total_units_sold", "Total Units Sold"
        elif any(w in q_lower for w in ["unit price", "price per unit"]):
            return "ROUND(AVG(unit_price), 2)", "avg_unit_price", "Average Unit Price"
        elif any(w in q_lower for w in ["order count", "number of orders", "number of transactions", "how many orders", "how many transactions", "total orders"]):
            return "COUNT(transaction_id)", "order_count", "Total Orders"
        elif any(w in q_lower for w in ["average revenue", "aov", "average order value", "average transaction"]):
            return "ROUND(AVG(net_revenue), 2)", "avg_net_revenue", "Average Net Revenue"
        else:
            # Default standard BI metric is Net Revenue
            return "SUM(net_revenue)", "total_net_revenue", "Net Revenue"

    def _resolve_dimension(self, q_lower: str) -> Tuple[Optional[str], Optional[str]]:
        """Identify GROUP BY dimension."""
        # Product dimension
        if any(w in q_lower for w in ["by product", "per product", "each product", "which product", "top product", "best product", "highest product"]):
            return "product", "product"

        # Category dimension
        if any(w in q_lower for w in ["by category", "per category", "each category", "which category"]):
            return "category", "category"

        # Region dimension
        if any(w in q_lower for w in ["by region", "per region", "each region", "which region", "highest sales region", "top region", "regional"]):
            return "region", "region"

        # Sales channel dimension
        if any(w in q_lower for w in ["by channel", "per channel", "sales channel", "which channel", "channel", "online vs retail", "retail vs online"]):
            return "sales_channel", "sales_channel"

        # Monthly time dimension
        if any(w in q_lower for w in ["monthly", "month trend", "revenue trend", "by month", "per month", "each month", "month-by-month", "monthly trend", "over time"]):
            return "year_month", "month"

        # Date dimension
        if any(w in q_lower for w in ["by date", "per date", "daily", "each day", "day by day"]):
            return "order_date", "order_date"

        # Status dimension
        if any(w in q_lower for w in ["by status", "per status", "completed vs returned"]):
            return "status", "status"

        return None, None

    def _resolve_ranking(self, q_lower: str) -> Dict[str, Any]:
        """Detect top N / bottom N / highest / lowest preferences."""
        info: Dict[str, Any] = {"direction": "DESC", "limit": None}

        # Check lowest / least / bottom
        if any(w in q_lower for w in ["lowest", "least", "bottom", "smallest", "worst", "minimum"]):
            info["direction"] = "ASC"

        # Check top N (e.g. top 3, top 5, top 10)
        match_top_n = re.search(r"\b(?:top|first|best|bottom)\s+(\d+)\b", q_lower)
        if match_top_n:
            info["limit"] = int(match_top_n.group(1))

        return info

    def _check_comparison(self, q_lower: str) -> Optional[Dict[str, Any]]:
        """Detect if the query asks to compare two months, two regions, or two channels."""
        # 1. Month comparison: "between [month1] and [month2]", "compare [month1] and [month2]", "from [month1] to [month2]"
        month_keys = list(self.MONTH_LOOKUP.keys())
        found_months = []
        for m_key in ["january", "february", "march", "april", "may", "june", "jan", "feb", "mar", "apr", "jun"]:
            if re.search(r"\b" + m_key + r"\b", q_lower):
                ym = self.MONTH_LOOKUP[m_key]
                if ym not in found_months:
                    found_months.append(ym)

        if len(found_months) >= 2 or ("between" in q_lower and "month" in q_lower):
            # Sort or maintain order
            if len(found_months) >= 2:
                m1, m2 = found_months[0], found_months[1]
            else:
                # Default to Jan and Feb if unspecified
                m1, m2 = "2026-01", "2026-02"
            return {
                "type": "month_comparison",
                "entity1": m1,
                "entity2": m2,
                "label1": self.MONTH_NAMES.get(m1, m1),
                "label2": self.MONTH_NAMES.get(m2, m2)
            }

        # 2. Region comparison (e.g. "compare North and South")
        found_regs = []
        for r_key, reg in self.REGION_SYNONYMS.items():
            if re.search(r"\b" + r_key + r"\b", q_lower):
                if reg not in found_regs:
                    found_regs.append(reg)
        if len(found_regs) == 2 and ("compare" in q_lower or "vs" in q_lower or "difference" in q_lower):
            return {
                "type": "region_comparison",
                "entity1": found_regs[0],
                "entity2": found_regs[1],
                "label1": found_regs[0],
                "label2": found_regs[1]
            }

        # 3. Channel comparison ("online vs retail")
        if ("online" in q_lower and "retail" in q_lower) and ("vs" in q_lower or "compare" in q_lower or "difference" in q_lower or "between" in q_lower):
            return {
                "type": "channel_comparison",
                "entity1": "Online",
                "entity2": "Retail",
                "label1": "Online",
                "label2": "Retail"
            }

        return None

    def _check_entity_listing(self, q_lower: str, filters: List[str]) -> Optional[Dict[str, str]]:
        """
        Detect if the user is asking to list distinct entities/products/categories/regions/channels.
        e.g., "what are the different products", "list all categories", "what regions exist"
        """
        # If user is asking for performance metrics/ranking/trends or metric calculations, do not treat as pure listing
        if any(w in q_lower for w in ["highest", "lowest", "top", "bottom", "best", "worst", "most", "least", "trend", "change", "between"]):
            return None

        # Do not match if asking for specific metric of an entity (e.g., "units of", "revenue of")
        if any(m in q_lower for m in ["units of", "revenue of", "discount of", "sales of", "price of", "how many units"]):
            return None

        # Check product listing
        if any(w in q_lower for w in ["product", "products", "items"]):
            # If a specific product filter is already extracted (e.g. "Office Chair"), do not treat as listing all products
            has_specific_product = any("product = " in f for f in filters)
            if not has_specific_product:
                if any(term in q_lower for term in [
                    "different product", "distinct product", "unique product", "available product",
                    "what are the product", "what are the different product", "which are the product",
                    "list of product", "list all product", "show all product", "names of product",
                    "types of product", "all product", "what product", "which product", "how many product"
                ]) or any(term in q_lower for term in [
                    "different items", "distinct items", "all items", "what items"
                ]):
                    return {"entity": "product", "label": "Products", "table_col": "product"}

        # Check category listing
        if any(w in q_lower for w in ["category", "categories"]):
            has_specific_category = any("category = " in f for f in filters)
            if not has_specific_category:
                if any(term in q_lower for term in [
                    "different categor", "distinct categor", "unique categor", "available categor",
                    "what are the categor", "which are the categor", "list of categor", "list all categor",
                    "show all categor", "all categor", "what categor", "which categor", "how many categor"
                ]):
                    return {"entity": "category", "label": "Categories", "table_col": "category"}

        # Check region listing
        if any(w in q_lower for w in ["region", "regions", "locations", "territories"]):
            has_specific_region = any("region = " in f for f in filters)
            if not has_specific_region:
                if any(term in q_lower for term in [
                    "different region", "distinct region", "unique region", "available region",
                    "what are the region", "which are the region", "list of region", "list all region",
                    "show all region", "all region", "what region", "which region", "how many region"
                ]):
                    return {"entity": "region", "label": "Regions", "table_col": "region"}

        # Check sales channel listing
        if any(w in q_lower for w in ["channel", "channels"]):
            has_specific_channel = any("sales_channel = " in f for f in filters)
            if not has_specific_channel:
                if any(term in q_lower for term in [
                    "different channel", "distinct channel", "unique channel", "available channel",
                    "what are the channel", "which are the channel", "list of channel", "list all channel",
                    "show all channel", "all channel", "what channel", "which channel", "how many channel"
                ]):
                    return {"entity": "sales_channel", "label": "Sales Channels", "table_col": "sales_channel"}

        return None

    def _build_entity_list_query(self, q_clean: str, entity_info: Dict[str, str], filters: List[str]) -> Dict[str, Any]:
        """Build SQL query for entity listing with supporting business aggregates."""
        ent = entity_info["entity"]
        col = entity_info["table_col"]
        label = entity_info["label"]

        where_clauses = list(filters)
        if not any("status" in f.lower() for f in filters):
            where_clauses.append("status = 'Completed'")
        where_str = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        if ent == "product":
            sql = (
                f"SELECT product, category, COUNT(transaction_id) AS total_orders, "
                f"SUM(quantity) AS total_units, SUM(net_revenue) AS total_net_revenue "
                f"FROM sales{where_str} "
                f"GROUP BY product, category "
                f"ORDER BY product ASC;"
            )
        elif ent == "category":
            sql = (
                f"SELECT category, COUNT(DISTINCT product) AS distinct_products, "
                f"COUNT(transaction_id) AS total_orders, SUM(quantity) AS total_units, "
                f"SUM(net_revenue) AS total_net_revenue "
                f"FROM sales{where_str} "
                f"GROUP BY category "
                f"ORDER BY total_net_revenue DESC;"
            )
        elif ent == "region":
            sql = (
                f"SELECT region, COUNT(transaction_id) AS total_orders, "
                f"SUM(quantity) AS total_units, SUM(net_revenue) AS total_net_revenue "
                f"FROM sales{where_str} "
                f"GROUP BY region "
                f"ORDER BY total_net_revenue DESC;"
            )
        else: # sales_channel
            sql = (
                f"SELECT sales_channel, COUNT(transaction_id) AS total_orders, "
                f"SUM(quantity) AS total_units, SUM(net_revenue) AS total_net_revenue "
                f"FROM sales{where_str} "
                f"GROUP BY sales_channel "
                f"ORDER BY total_net_revenue DESC;"
            )

        return {
            "question": q_clean,
            "intent": QueryIntent.ENTITY_LIST,
            "sql": sql,
            "description": f"List of distinct {label.lower()} with supporting figures",
            "dimension": col,
            "metric_name": "Net Revenue",
            "metric_alias": "total_net_revenue",
            "entity_info": entity_info,
            "is_breakdown": True
        }

    def _build_comparison_query(self, q_clean: str, comp_info: Dict[str, Any], filters: List[str]) -> Dict[str, Any]:
        """Build SQL query for comparative analytics."""
        comp_type = comp_info["type"]
        e1, e2 = comp_info["entity1"], comp_info["entity2"]
        l1, l2 = comp_info["label1"], comp_info["label2"]

        if comp_type == "month_comparison":
            sql = (
                f"SELECT year_month AS period, "
                f"SUM(net_revenue) AS total_net_revenue, "
                f"SUM(gross_revenue) AS total_gross_revenue, "
                f"SUM(discount_amount) AS total_discounts, "
                f"SUM(quantity) AS total_units, "
                f"COUNT(transaction_id) AS total_orders "
                f"FROM sales "
                f"WHERE status = 'Completed' AND year_month IN ('{e1}', '{e2}') "
                f"GROUP BY year_month "
                f"ORDER BY year_month ASC;"
            )
            desc = f"Revenue and sales comparison between {l1} and {l2}"
            dim = "period"

        elif comp_type == "region_comparison":
            sql = (
                f"SELECT region, "
                f"SUM(net_revenue) AS total_net_revenue, "
                f"SUM(quantity) AS total_units, "
                f"COUNT(transaction_id) AS total_orders "
                f"FROM sales "
                f"WHERE status = 'Completed' AND region IN ('{e1}', '{e2}') "
                f"GROUP BY region;"
            )
            desc = f"Sales performance comparison between {l1} and {l2} regions"
            dim = "region"

        else: # channel_comparison
            sql = (
                f"SELECT sales_channel, "
                f"SUM(net_revenue) AS total_net_revenue, "
                f"SUM(quantity) AS total_units, "
                f"COUNT(transaction_id) AS total_orders "
                f"FROM sales "
                f"WHERE status = 'Completed' "
                f"GROUP BY sales_channel;"
            )
            desc = "Sales performance comparison between Online and Retail channels"
            dim = "sales_channel"

        return {
            "question": q_clean,
            "intent": QueryIntent.COMPARISON,
            "sql": sql,
            "description": desc,
            "comparison_info": comp_info,
            "dimension": dim,
            "metric_name": "Net Revenue",
            "metric_alias": "total_net_revenue",
            "is_breakdown": True
        }

    def _build_record_list_query(self, q_clean: str, q_lower: str, filters: List[str]) -> Dict[str, Any]:
        """Build query to display detailed records."""
        where_clauses = list(filters)

        # Check if discount filter mentioned
        if "discount > 0" in q_lower or "discounted" in q_lower or "with discount" in q_lower:
            if not any("discount_amount" in f for f in where_clauses):
                where_clauses.append("discount_amount > 0")

        # Check limit
        limit_match = re.search(r"\b(?:first|top|limit)\s+(\d+)\b", q_lower)
        limit_str = f" LIMIT {limit_match.group(1)}" if limit_match else " LIMIT 20"

        where_str = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        sql = (
            f"SELECT transaction_id, order_date, product, category, region, "
            f"sales_channel, quantity, unit_price, discount_amount, net_revenue, status "
            f"FROM sales{where_str} "
            f"ORDER BY net_revenue DESC{limit_str};"
        )

        return {
            "question": q_clean,
            "intent": QueryIntent.RECORD_LOOKUP,
            "sql": sql,
            "description": "List of matching sales transactions",
            "dimension": None,
            "metric_name": "Transaction Records",
            "is_breakdown": False
        }
