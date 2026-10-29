"""
Streamlit User Interface for Mini AI Business Intelligence Assistant.
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import pandas as pd
from src.analytics.engine import AnalyticsEngine
from src.database.connection import get_ro_connection
from src.ai.sql_guardrails import SQLSecurityError

st.set_page_config(
    page_title="SalesAgent IQ",
    page_icon="🤖",
    layout="wide"
)

# Custom Styling
st.markdown("""
<style>
    .main-title { font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem; color: #1e293b; }
    .sub-title { font-size: 1rem; color: #64748b; margin-bottom: 1.5rem; }
    .kpi-box { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; text-align: center; }
    .kpi-val { font-size: 1.6rem; font-weight: 700; color: #0284c7; }
    .kpi-lbl { font-size: 0.85rem; color: #64748b; text-transform: uppercase; }
    .answer-box { background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 1.25rem; border-radius: 4px; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🤖 SalesAgent IQ</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Natural Language SQL &bull; Vectorless RAG &bull; Read-Only Guardrails</div>', unsafe_allow_html=True)

# Top KPI ribbon
try:
    conn = get_ro_connection()
    kpi_df = pd.read_sql_query("""
        SELECT 
            SUM(net_revenue) AS total_revenue,
            COUNT(*) AS total_orders,
            SUM(quantity) AS total_units,
            SUM(discount_amount) AS total_discounts
        FROM sales WHERE status = 'Completed';
    """, conn)
    conn.close()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-lbl">Total Net Revenue</div>
            <div class="kpi-val">${kpi_df['total_revenue'].iloc[0]:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-lbl">Completed Orders</div>
            <div class="kpi-val">{kpi_df['total_orders'].iloc[0]}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-lbl">Units Sold</div>
            <div class="kpi-val">{kpi_df['total_units'].iloc[0]:,}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-box">
            <div class="kpi-lbl">Discounts Applied</div>
            <div class="kpi-val">${kpi_df['total_discounts'].iloc[0]:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
except Exception as e:
    st.warning(f"Could not load KPI ribbon: {e}")

st.write("")

# Query Input
engine = AnalyticsEngine()

st.subheader("💬 Ask Any Question About the Sales Data")
sample_questions = [
    "What is the total revenue?",
    "Which product generated the highest revenue?",
    "What is the monthly revenue trend?",
    "Which region generated the highest sales?",
    "How did revenue change between two months?",
    "What are the different products?",
    "What are the categories?",
    "What are the regions?",
    "How many units of Office Chair were sold in South region?",
    "What is the total discount given in Electronics?",
    "Compare online and retail sales",
    "List all returned orders"
]

selected_chip = st.selectbox("Quick question selector (or type your own below):", ["-- Choose a suggested question --"] + sample_questions)

default_text = selected_chip if selected_chip != "-- Choose a suggested question --" else ""
user_question = st.text_input("Enter your natural language question:", value=default_text)

if st.button("🚀 Run BI Analysis", type="primary"):
    if not user_question.strip():
        st.error("Please enter a question.")
    else:
        with st.spinner("Processing natural language query with Vectorless RAG..."):
            try:
                res = engine.process_question(user_question.strip())

                # Answer Summary
                st.markdown(f"""
                <div class="answer-box">
                    <h4 style="margin-top:0; color:#1e40af;">💡 Answer</h4>
                    <p style="font-size: 1.15rem; font-weight: 500; color: #1e293b; margin: 0;">{res['summary']}</p>
                    <small style="color: #64748b;">Execution time: {res['execution_time_ms']}ms | Engine: {res['ai_source']}</small>
                </div>
                """, unsafe_allow_html=True)

                # Comparison metrics
                if res.get("comparative_metrics"):
                    comp = res["comparative_metrics"]
                    c1, c2, c3 = st.columns(3)
                    c1.metric(comp["entity1"]["name"], f"${comp['entity1']['revenue']:,.2f}")
                    c2.metric(comp["entity2"]["name"], f"${comp['entity2']['revenue']:,.2f}")
                    c3.metric("Variance", f"${comp['absolute_difference']:,.2f}", f"{comp['percentage_change']}%")

                # SQL Expander
                with st.expander("🔍 Inspect Generated SQL Query (Safe Read-Only)", expanded=True):
                    st.code(res["sql_query"], language="sql")
                    st.caption("🛡️ Verified: Read-only execution via SQLite URI mode.")

                # Chart Visualization
                chart = res.get("chart_data")
                if chart and chart.get("labels") and chart.get("values"):
                    st.subheader("📈 Visualization")
                    chart_df = pd.DataFrame({
                        "Dimension": chart["labels"],
                        "Value": chart["values"]
                    }).set_index("Dimension")

                    if chart.get("type") == "line":
                        st.line_chart(chart_df)
                    else:
                        st.bar_chart(chart_df)

                # Supporting Data Table
                st.subheader(f"📋 Supporting Data Figures ({res['row_count']} rows)")
                if res["supporting_data"]:
                    df_out = pd.DataFrame(res["supporting_data"])
                    st.dataframe(df_out, use_container_width=True)
                else:
                    st.info("No records returned.")

            except SQLSecurityError as s_err:
                st.error(f"🛡️ Security Guardrail Blocked Query: {s_err}")
            except Exception as e:
                st.error(f"Execution Error: {e}")

# Sidebar
with st.sidebar:
    st.header("ℹ️ Architecture & Data Hygiene")
    st.markdown("""
    **Vectorless RAG Engine:**
    - Deterministic schema linking
    - Direct SQLite relational queries
    - Imputation audit on TXN0051 (Laptop Stand price: $1,200)
    - Returns isolation on TXN0033
    - Defense-in-depth read-only URI
    """)
    st.markdown("---")
    st.caption("SalesAgent IQ &bull; GET AI-Assisted Assessment 2026")
