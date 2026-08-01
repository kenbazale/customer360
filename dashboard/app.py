"""
app.py
Customer 360 Analytics Dashboard — reads directly from Snowflake's
mart.customer_360 table and gives a relationship-manager-style view of
customer risk and engagement.

Run locally:
    streamlit run app.py

Deploy: push this repo to GitHub, then deploy via share.streamlit.io,
pointing at this file. Add Snowflake credentials as Streamlit Cloud
"Secrets" (see secrets.toml.template for the required keys).
"""

import pandas as pd
import plotly.express as px
import snowflake.connector
import streamlit as st

st.set_page_config(
    page_title="Customer 360 — Retail Banking Analytics",
    page_icon="🏦",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"],
    )


@st.cache_data(ttl=600)
def load_customer_360():
    conn = get_connection()
    query = "SELECT * FROM mart.customer_360"
    return pd.read_sql(query, conn)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
try:
    df = load_customer_360()
except Exception as e:
    st.error(
        "Could not connect to Snowflake. Check that your secrets.toml "
        "(local) or Streamlit Cloud Secrets (deployed) has the correct "
        "connection details."
    )
    st.exception(e)
    st.stop()

df.columns = [c.lower() for c in df.columns]

# ---------------------------------------------------------------------------
# Header + KPIs
# ---------------------------------------------------------------------------
st.title("🏦 Customer 360 — Retail Banking Analytics")
st.caption(
    "Unified customer view combining account activity, loan status, and "
    "digital engagement. Built on synthetic data with an FCUBS-style "
    "core banking shape."
)

total_customers = len(df)
high_dormancy_pct = (df["dormancy_risk"] == "high").mean() * 100
at_risk_loans_pct = (
    df["delinquency_status"].isin(["arrears", "default_risk"]).mean() * 100
)
avg_engagement = df["engagement_score"].mean()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total Customers", f"{total_customers:,}")
kpi2.metric("High Dormancy Risk", f"{high_dormancy_pct:.1f}%")
kpi3.metric("Loans in Arrears/Default Risk", f"{at_risk_loans_pct:.1f}%")
kpi4.metric("Avg Engagement Score", f"{avg_engagement:.1f} / 100")

st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_search, tab_risk = st.tabs(
    ["📊 Overview", "🔍 Customer Search", "⚠️ Risk Table"]
)

with tab_overview:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dormancy Risk Distribution")
        dormancy_counts = df["dormancy_risk"].value_counts().reset_index()
        dormancy_counts.columns = ["dormancy_risk", "count"]
        fig = px.pie(
            dormancy_counts,
            names="dormancy_risk",
            values="count",
            color="dormancy_risk",
            color_discrete_map={
                "low": "#2ca02c",
                "medium": "#ff7f0e",
                "high": "#d62728",
                "unknown": "#7f7f7f",
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Delinquency Status Distribution")
        delinq_counts = df["delinquency_status"].value_counts().reset_index()
        delinq_counts.columns = ["delinquency_status", "count"]
        fig = px.bar(
            delinq_counts,
            x="delinquency_status",
            y="count",
            color="delinquency_status",
            category_orders={
                "delinquency_status": [
                    "no_loan", "current", "watch", "arrears", "default_risk"
                ]
            },
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Customer Segment Breakdown")
        seg_counts = df["segment"].value_counts().reset_index()
        seg_counts.columns = ["segment", "count"]
        fig = px.bar(seg_counts, x="segment", y="count", color="segment")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.subheader("Engagement Score Distribution")
        fig = px.histogram(df, x="engagement_score", nbins=20)
        st.plotly_chart(fig, use_container_width=True)

with tab_search:
    st.subheader("Look up a customer")
    search_term = st.text_input("Search by customer name or ID")

    if search_term:
        matches = df[
            df["full_name"].str.contains(search_term, case=False, na=False)
            | df["customer_id"].astype(str).str.contains(search_term, case=False, na=False)
        ]

        if matches.empty:
            st.warning("No customers found matching that search.")
        else:
            for _, row in matches.head(20).iterrows():
                with st.expander(f"{row['full_name']} — {row['customer_id']}"):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Segment:** {row['segment']}")
                    c1.write(f"**Branch:** {row['branch_code']}")
                    c1.write(f"**Tenure:** {row['tenure_years']} years")

                    c2.write(f"**Dormancy Risk:** {row['dormancy_risk']}")
                    c2.write(f"**Delinquency Status:** {row['delinquency_status']}")
                    c2.write(f"**KYC Score:** {row['kyc_completeness_score']}")

                    c3.write(f"**Engagement Score:** {row['engagement_score']:.0f} / 100")
                    c3.write(f"**Total Accounts:** {row['total_accounts']}")
                    c3.write(f"**Total Balance:** {row['total_balance']:,.2f}")
    else:
        st.info("Enter a name or customer ID above to search.")

with tab_risk:
    st.subheader("Filterable Risk Table")
    st.caption(
        "The screen a relationship manager or collections team would "
        "actually use — filter to the customers that need attention."
    )

    filt1, filt2, filt3 = st.columns(3)
    with filt1:
        dormancy_filter = st.multiselect(
            "Dormancy Risk",
            options=sorted(df["dormancy_risk"].dropna().unique()),
            default=[],
        )
    with filt2:
        delinquency_filter = st.multiselect(
            "Delinquency Status",
            options=sorted(df["delinquency_status"].dropna().unique()),
            default=[],
        )
    with filt3:
        segment_filter = st.multiselect(
            "Segment",
            options=sorted(df["segment"].dropna().unique()),
            default=[],
        )

    filtered = df.copy()
    if dormancy_filter:
        filtered = filtered[filtered["dormancy_risk"].isin(dormancy_filter)]
    if delinquency_filter:
        filtered = filtered[filtered["delinquency_status"].isin(delinquency_filter)]
    if segment_filter:
        filtered = filtered[filtered["segment"].isin(segment_filter)]

    st.write(f"Showing {len(filtered):,} of {len(df):,} customers")
    st.dataframe(
        filtered[
            [
                "customer_id", "full_name", "segment", "branch_code",
                "dormancy_risk", "delinquency_status", "kyc_completeness_score",
                "engagement_score", "total_balance",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )