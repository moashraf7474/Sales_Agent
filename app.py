"""Streamlit UI for the Sales Insights Agent.  Run:  streamlit run app.py"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from agent import Agent

load_dotenv()

st.set_page_config(page_title="Sales Insights Agent", page_icon="📊", layout="wide")
st.title("📊 Sales Insights Agent")
st.caption("Upload a sales file to see the dashboard, key insights, trends, and recommendations.")

DASHBOARD_PROMPT = (
    "Build a complete sales dashboard: "
    "1) Add 4 key number cards with add_kpi (total revenue, number of orders, average order value, best-selling product). "
    "2) Plot a chart of the top 10 best-selling products, a chart of the lowest-selling (stagnant) products, and a chart of revenue over time. "
    "3) If there is a city, branch, or category column, plot a chart for it. "
    "4) At the end, write insights and recommendations."
)

# ---------- Sidebar ----------
with st.sidebar:
    api_key = st.text_input(
        "OpenRouter API Key",
        type="password",
        value=os.getenv("OPENROUTER_API_KEY", ""),
        help="Create a free key at openrouter.ai",
    )
    uploaded = st.file_uploader("Sales file", type=["csv", "xlsx", "xls"])


def load_df(file) -> pd.DataFrame:
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(file)
    return pd.read_excel(file)


if not uploaded:
    st.info("Start by uploading a CSV or Excel file from the sidebar. (Sample file: run make_sample_data.py)")
    st.stop()

df = load_df(uploaded)

def find_column(names):
    normalized = {str(name).strip().lower().replace(" ", "_"): name for name in df.columns}
    for name in names:
        if name in normalized:
            return normalized[name]
    return None

date_col = find_column(["date", "order_date", "sales_date", "day"])
product_col = find_column(["product", "product_name", "item", "item_name", "sku"])
city_col = find_column(["city", "branch", "location", "region", "category"])
quantity_col = find_column(["quantity", "qty", "units", "order_quantity"])
unit_price_col = find_column(["unit_price", "price", "unitprice", "selling_price"])
total_col = find_column(["total", "revenue", "sales", "amount", "sales_amount"])

if total_col is not None:
    revenue = pd.to_numeric(df[total_col], errors="coerce").fillna(0)
elif quantity_col is not None and unit_price_col is not None:
    revenue = pd.to_numeric(df[quantity_col], errors="coerce").fillna(0) * pd.to_numeric(df[unit_price_col], errors="coerce").fillna(0)
else:
    revenue = pd.Series(0.0, index=df.index)

total_revenue = float(revenue.sum())
order_count = int(len(df))
average_order = float(revenue.mean()) if order_count else 0.0

if product_col is not None:
    product_revenue = pd.DataFrame({"product": df[product_col].astype(str), "revenue": revenue})
    product_summary = product_revenue.groupby("product", as_index=False)["revenue"].sum()
    product_summary = product_summary.sort_values("revenue", ascending=False)
    best_selling_product = str(product_summary.iloc[0]["product"]) if not product_summary.empty else "N/A"
else:
    product_summary = pd.DataFrame(columns=["product", "revenue"])
    best_selling_product = "N/A"

# The AI agent is used only for optional follow-up questions.
if st.session_state.get("file_name") != uploaded.name or st.session_state.get("api_key") != api_key:
    st.session_state.file_name = uploaded.name
    st.session_state.api_key = api_key
    st.session_state.answers = []
    if api_key:
        st.session_state.agent = Agent(df, api_key=api_key)

agent = st.session_state.get("agent")

with st.expander("Data preview", expanded=False):
    st.dataframe(df.head(20), hide_index=True, width="stretch")


def ask(question: str):
    if agent is None:
        st.session_state.answers.append((question, "Enter an OpenRouter API Key in the sidebar to ask follow-up questions."))
        return
    with st.status("Analyzing...", state="running", expanded=False) as status:
        try:
            answer = agent.run(question)
            status.update(label="Analysis complete", state="complete")
        except Exception as e:
            status.update(label="Analysis failed", state="error")
            answer = f"An error occurred: {e}"
    st.session_state.answers.append((question, answer))


# ---------- Main dashboard ----------
metric_values = [
    ("Total revenue", f"${total_revenue:,.2f}", None),
    ("Number of orders", f"{order_count:,}", None),
    ("Average order", f"${average_order:,.2f}", None),
    ("Best-selling product", best_selling_product, None),
]
metrics = st.columns(4)
for metric, (label, value, _) in zip(metrics, metric_values):
    metric.metric(label, value, border=True)

st.markdown("### Sales trends")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    with st.container(border=True):
        if date_col is not None:
            dates = pd.to_datetime(df[date_col], errors="coerce")
            trend = pd.DataFrame({"date": dates, "revenue": revenue}).dropna()
            trend = trend.groupby("date", as_index=False)["revenue"].sum().sort_values("date")
            if not trend.empty:
                st.plotly_chart(
                    px.line(trend, x="date", y="revenue", markers=True, title="Revenue over time"),
                    width="stretch",
                    key="revenue_trend",
                )
            else:
                st.info("No valid dates were found.")
        else:
            st.info("Add a date column to see revenue over time.")

with chart_col2:
    with st.container(border=True):
        if not product_summary.empty:
            top_products = product_summary.head(10)
            st.plotly_chart(
                px.bar(top_products, x="revenue", y="product", orientation="h", title="Top 10 products"),
                width="stretch",
                key="top_products",
            )
        else:
            st.info("Add a product column to compare sales.")

chart_col3, chart_col4 = st.columns(2)
with chart_col3:
    with st.container(border=True):
        if city_col is not None:
            city_summary = pd.DataFrame({"location": df[city_col].astype(str), "revenue": revenue})
            city_summary = city_summary.groupby("location", as_index=False)["revenue"].sum().sort_values("revenue", ascending=False)
            if not city_summary.empty:
                st.plotly_chart(
                    px.bar(city_summary, x="location", y="revenue", title="Revenue by location"),
                    width="stretch",
                    key="location_revenue",
                )
        else:
            st.info("Add a city, branch, region, or category column.")

with chart_col4:
    with st.container(border=True):
        if not product_summary.empty:
            stagnant = product_summary.tail(min(10, len(product_summary))).sort_values("revenue")
            st.plotly_chart(
                px.bar(stagnant, x="revenue", y="product", orientation="h", title="Lowest-selling products"),
                width="stretch",
                key="stagnant_products",
            )

st.markdown("### Important insights")
insight_col1, insight_col2 = st.columns([2, 1])
with insight_col1:
    if not product_summary.empty:
        top = product_summary.iloc[0]
        bottom = product_summary.iloc[-1]
        top_share = (float(top["revenue"]) / total_revenue * 100) if total_revenue else 0
        st.success(
            f"**Main finding:** {top['product']} leads sales with "
            f"${float(top['revenue']):,.2f}, representing {top_share:.1f}% of total revenue."
        )
        st.info(
            f"**Review opportunity:** {bottom['product']} generated "
            f"${float(bottom['revenue']):,.2f}. Consider a promotion, bundle, or demand check."
        )
    else:
        st.info("The dashboard needs a product or item column to identify winners and opportunities.")

with insight_col2:
    st.download_button(
        "Download sales data",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="sales_dashboard.csv",
        mime="text/csv",
        width="stretch",
    )

st.markdown("### Ask a detailed question")
question = st.chat_input("Ask about this data...")
if question:
    ask(question)

for q, a in st.session_state.get("answers", []):
    with st.chat_message("user"):
        st.write(q)
    with st.chat_message("assistant"):
        st.write(a)
