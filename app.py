import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os
import sys
from dotenv import load_dotenv
from google import genai

# --- PATHS & CONFIG ---
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_RUNS_DIR = os.path.join(ROOT_DIR, "python_runs")
DB_PATH = os.path.join(ROOT_DIR, "ecommerce.db")
MODEL = "gemini-3.1-flash-lite"

# make python_runs importable so we can call database_setup directly
sys.path.insert(0, PYTHON_RUNS_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"), override=True)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- AUTO BUILD DATABASE IF IT DOESN'T EXIST ---
if not os.path.exists(DB_PATH):
    st.info("Building database for the first time. Please wait about 60 seconds...")
    from database_setup import build_ecommerce_db
    build_ecommerce_db()
    st.rerun()

SCHEMA = """
You are an expert Data Analyst working with the E-commerce SQLite database.
Your only job is to convert natural language questions into valid SQLite queries.
Return ONLY the raw SQL query. No markdown, no backticks, no explanation.

Tables available:
1. customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
2. orders (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_customer_date, order_estimated_delivery_date)
3. order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value)
4. order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value)
5. order_reviews (review_id, order_id, review_score, review_creation_date, review_answer_timestamp)
6. products (product_id, product_category_name, product_name_lenght, product_description_lenght, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm)
7. sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state)
8. geolocation (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state)
9. category_translation (product_category_name, product_category_name_english)

RULES:
- Always JOIN category_translation to show English category names
- For revenue always use SUM(order_items.price)
- Always add LIMIT 10 unless user asks for more
- Only write SELECT queries, never DELETE UPDATE or INSERT
- Always give columns descriptive aliases e.g. 'Total Revenue' instead of 'SUM(price)'
"""


def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Fraunces:ital,wght@0,400;0,700;1,400&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #1A1A2E;
    }

    .stApp {
        background-color: #F5F4F0;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #D9D3C7;
    }

    [data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #4A4560;
        margin-bottom: 0.8rem;
    }

    [data-testid="stSidebar"] .stButton button {
        background: #FFFFFF;
        border: 1px solid #D9D3C7;
        border-radius: 10px;
        color: #1A1A2E;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.85rem;
        font-weight: 500;
        padding: 0.65rem 0.9rem;
        text-align: left;
        transition: all 0.18s ease;
        margin-bottom: 5px;
        line-height: 1.45;
    }

    [data-testid="stSidebar"] .stButton button:hover {
        background: #FFF4DC;
        border-color: #C9962B;
        color: #1A1A2E;
        transform: translateX(3px);
    }

    /* ── MAIN HEADER ── */
    .header-wrap {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        margin-bottom: 1.8rem;
        position: relative;
        overflow: hidden;
    }

    .header-wrap::before {
        content: '';
        position: absolute;
        top: -40px;
        right: -40px;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(242, 199, 92, 0.2) 0%, transparent 70%);
        border-radius: 50%;
    }

    .header-wrap::after {
        content: '';
        position: absolute;
        bottom: -30px;
        left: 30%;
        width: 150px;
        height: 150px;
        background: radial-gradient(circle, rgba(242, 199, 92, 0.1) 0%, transparent 70%);
        border-radius: 50%;
    }

    .header-badge {
        display: inline-block;
        background: rgba(242, 199, 92, 0.18);
        border: 1px solid rgba(242, 199, 92, 0.5);
        border-radius: 20px;
        padding: 0.25rem 0.9rem;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #F2C75C;
        margin-bottom: 1rem;
    }

    .header-title {
        font-family: 'Fraunces', serif;
        font-size: 3rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
        margin: 0 0 0.8rem 0;
        letter-spacing: -0.02em;
    }

    .header-title span {
        color: #F2C75C;
    }

    .header-subtitle {
        font-size: 1rem;
        color: rgba(255,255,255,0.88);
        font-weight: 400;
        max-width: 560px;
        line-height: 1.6;
        margin: 0;
    }

    /* ── STATS ROW ── */
    .stats-row {
        display: flex;
        gap: 12px;
        margin-bottom: 1.8rem;
    }

    .stat-pill {
        flex: 1;
        background: #FFFFFF;
        border: 1px solid #D9D3C7;
        border-radius: 14px;
        padding: 1.2rem;
        text-align: center;
        transition: box-shadow 0.2s;
    }

    .stat-pill:hover {
        box-shadow: 0 4px 20px rgba(26,26,46,0.1);
    }

    .stat-num {
        font-family: 'Fraunces', serif;
        font-size: 1.9rem;
        font-weight: 700;
        color: #1A1A2E;
        display: block;
        line-height: 1;
    }

    .stat-lbl {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #4A4560;
        display: block;
        margin-top: 0.5rem;
    }

    /* ── CHAT MESSAGES ── */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #FFFFFF !important;
        border: 1px solid #D9D3C7 !important;
        border-radius: 14px !important;
        padding: 1rem 1.4rem !important;
        margin-bottom: 8px;
    }

    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: #FFF8EE !important;
        border: 1px solid #E8D9B5 !important;
        border-radius: 14px !important;
        padding: 1rem 1.4rem !important;
        margin-bottom: 16px;
    }

    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li {
        color: #1A1A2E !important;
        font-size: 0.95rem;
    }

    /* ── CHAT INPUT ── */
    [data-testid="stChatInput"] {
        background: #FFFFFF !important;
        border: 2px solid #C9C0B0 !important;
        border-radius: 16px !important;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #C9962B !important;
        box-shadow: 0 0 0 4px rgba(201, 150, 43, 0.15) !important;
    }

    [data-testid="stChatInput"] textarea {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #1A1A2E !important;
        font-size: 0.95rem !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #6B6478 !important;
        opacity: 1 !important;
    }

    /* ── EXPANDER ── */
    [data-testid="stExpander"] {
        background: #FFFFFF !important;
        border: 1px solid #D9D3C7 !important;
        border-radius: 12px !important;
    }

    [data-testid="stExpander"] summary {
        color: #1A1A2E !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* ── DATAFRAME ── */
    [data-testid="stDataFrame"] {
        border: 1px solid #D9D3C7 !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        background: #FFFFFF !important;
    }

    /* ── ALERTS ── */
    [data-testid="stAlert"] {
        border-radius: 12px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.9rem !important;
    }

    /* ── DIVIDER ── */
    hr { border-color: #D9D3C7 !important; }

    /* ── FOOTER ── */
    .footer-txt {
        font-size: 0.8rem;
        color: #4A4560;
        text-align: center;
        letter-spacing: 0.04em;
        padding: 0.5rem 0 1rem;
    }

    /* scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #F5F4F0; }
    ::-webkit-scrollbar-thumb { background: #C9C0B0; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)


def generate_chart(df):
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()

    clean_theme = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.7)",
        font=dict(family="Plus Jakarta Sans", color="#1A1A2E", size=13),
        xaxis=dict(
            gridcolor="#ECE8DF",
            linecolor="#C9C0B0",
            tickfont=dict(color="#2D2842", size=12)
        ),
        yaxis=dict(
            gridcolor="#ECE8DF",
            linecolor="#C9C0B0",
            tickfont=dict(color="#2D2842", size=12)
        ),
        margin=dict(l=20, r=20, t=30, b=60),
        hoverlabel=dict(
            bgcolor="#1A1A2E",
            bordercolor="#F2C75C",
            font=dict(family="Plus Jakarta Sans", color="#FFFFFF")
        )
    )

    if len(numeric_cols) >= 1 and len(text_cols) >= 1:
        fig = px.bar(
            df,
            x=text_cols[0],
            y=numeric_cols[0],
            color=numeric_cols[0],
            color_continuous_scale=[[0, "#F0E6CC"], [0.5, "#D4A843"], [1, "#1A1A2E"]]
        )
        fig.update_traces(
            marker_line_width=0,
            hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>"
        )
        fig.update_layout(**clean_theme)
        fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=-35)
        return fig

    elif len(numeric_cols) >= 2:
        fig = px.scatter(
            df,
            x=numeric_cols[0],
            y=numeric_cols[1],
            color_discrete_sequence=["#B8860B"]
        )
        fig.update_traces(marker=dict(size=9, opacity=0.8))
        fig.update_layout(**clean_theme)
        return fig

    return None


# ══════════════════════════════
#  APP
# ══════════════════════════════
st.set_page_config(
    page_title="Natural Language Query — E-commerce Intelligence",
    page_icon="🛒",
    layout="wide"
)

inject_css()

# ── SIDEBAR ──
with st.sidebar:
    st.markdown("""
    <div style='padding: 1.2rem 0 1rem 0;'>
        <div style='font-family: Fraunces, serif; font-size: 1.4rem; font-weight: 700; color: #1A1A2E;'>Natural Language Query</div>
        <div style='font-size: 0.75rem; color: #4A4560; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 4px; font-weight: 600;'>E-commerce Intelligence</div>
    </div>
    <hr style='border-color: #D9D3C7; margin-bottom: 1.2rem;'>
    """, unsafe_allow_html=True)

    st.markdown("### 💡 Try these questions")

    suggestions = [
        "What are the top 5 product categories by total revenue?",
        "Which state has the most customers?",
        "What are the top 10 categories by average review score?",
        "Which 10 categories have the lowest average review score?",
        "How many orders were delivered successfully?",
        "Which payment type is most popular?",
        "What are the top 5 sellers by total sales?",
        "What is the total revenue per year?"
    ]

    for s in suggestions:
        if st.button(s, use_container_width=True):
            st.session_state.suggestion = s

    st.markdown("""
    <hr style='border-color: #D9D3C7; margin-top: 1.5rem;'>
    <div style='font-size: 0.8rem; color: #2D2842; line-height: 1.9; padding-top: 0.4rem; font-weight: 500;'>
        🔒 Read-only secure connection<br>
        ⚡ Powered by Gemini 3.1 Flash Lite<br>
        🗄️ 1.6M rows · 9 tables
    </div>
    """, unsafe_allow_html=True)

# ── HEADER ──
st.markdown("""
<div class="header-wrap">
    <div class="header-badge">AI-Powered · Natural Language · SQL</div>
    <h1 class="header-title">Natural Language <span>Query</span></h1>
    <p class="header-subtitle">Ask any business question in plain English and get instant answers from 1.6 million rows of real e-commerce data.</p>
</div>
""", unsafe_allow_html=True)

# ── STATS ──
st.markdown("""
<div class="stats-row">
    <div class="stat-pill"><span class="stat-num">1.6M</span><span class="stat-lbl">Total Rows</span></div>
    <div class="stat-pill"><span class="stat-num">9</span><span class="stat-lbl">Linked Tables</span></div>
    <div class="stat-pill"><span class="stat-num">99K+</span><span class="stat-lbl">Orders</span></div>
    <div class="stat-pill"><span class="stat-num">32K+</span><span class="stat-lbl">Products</span></div>
    <div class="stat-pill"><span class="stat-num">3K+</span><span class="stat-lbl">Sellers</span></div>
</div>
""", unsafe_allow_html=True)

# ── SESSION STATE ──
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# ── CHAT HISTORY ──
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sql" in message:
            with st.expander("🔍 View generated SQL"):
                st.code(message["sql"], language="sql")
        if "data" in message:
            fig = generate_chart(message["data"])
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            st.dataframe(message["data"], use_container_width=True)

# ── CHAT INPUT ──
default = st.session_state.pop("suggestion", "")

if st.session_state.is_processing:
    st.chat_input("Please wait — query is running...", disabled=True)
    prompt = None
else:
    prompt = st.chat_input("Ask a business question e.g. What are the top 10 cities by number of orders?")

question = default or prompt

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    st.session_state.is_processing = True

    with st.chat_message("assistant"):
        with st.spinner("Analysing your question..."):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=SCHEMA + f"\n\nUser Question: {question}\nSQL Query:"
                )

                sql = response.text.strip()
                sql = sql.replace("```sql", "").replace("```", "").strip()

                with st.expander("🔍 View generated SQL"):
                    st.code(sql, language="sql")

                conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
                df = pd.read_sql_query(sql, conn)
                conn.close()

                if df.empty:
                    st.warning("No results found. Try rephrasing your question.")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "No results found for that question.",
                        "sql": sql
                    })
                else:
                    st.success(f"✓ {len(df)} rows returned")

                    fig = generate_chart(df)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

                    st.dataframe(df, use_container_width=True)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Here are the results for: *{question}*",
                        "sql": sql,
                        "data": df
                    })

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    st.warning("⏳ Rate limit reached. Please wait 1-2 minutes before asking another question.")
                else:
                    st.error(f"Something went wrong: {e}")

            finally:
                st.session_state.is_processing = False

# ── FOOTER ──
st.divider()
st.markdown("""
<p class="footer-txt">NATURAL LANGUAGE QUERY &nbsp;·&nbsp; Gemini 3.1 Flash Lite &nbsp;·&nbsp; SQLite &nbsp;·&nbsp; Streamlit &nbsp;·&nbsp; E-commerce Dataset &nbsp;·&nbsp; Read-only secure connection</p>
""", unsafe_allow_html=True)