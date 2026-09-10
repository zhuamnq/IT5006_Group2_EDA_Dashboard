from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(page_title="Olist Explorer", page_icon="🛒", layout="wide")
DATA = Path(__file__).with_name("data") / "olist_dashboard.csv.gz"


@st.cache_data
def load_data():
    return pd.read_csv(DATA, parse_dates=["order_purchase_timestamp"])


def multiselect(label, values):
    options = sorted(values.dropna().unique())
    return st.sidebar.multiselect(label, options, placeholder="All")


data = load_data()
st.title("🛒 Olist E-commerce Explorer")
st.caption("Explore when, where and what customers bought, and how delivery performance relates to reviews.")

st.sidebar.header("Filters")
minimum, maximum = data.order_purchase_timestamp.dt.date.agg(["min", "max"])
dates = st.sidebar.date_input("Purchase date", (minimum, maximum), min_value=minimum, max_value=maximum)
customer_states = multiselect("Customer state", data.customer_state)
seller_states = multiselect("Seller state", data.seller_state)
categories = multiselect("Product category", data.product_category)
statuses = multiselect("Order status", data.order_status)
delivery_statuses = multiselect("Delivery status", data.delivery_status)

filtered = data.copy()
if len(dates) == 2:
    filtered = filtered[filtered.order_purchase_timestamp.dt.date.between(*dates)]
for column, selected in {
    "customer_state": customer_states,
    "seller_state": seller_states,
    "product_category": categories,
    "order_status": statuses,
    "delivery_status": delivery_statuses,
}.items():
    if selected:
        filtered = filtered[filtered[column].isin(selected)]

if filtered.empty:
    st.warning("No records match these filters.")
    st.stop()

orders = filtered.drop_duplicates("order_id")
delivered = orders[orders.delivery_status != "Unknown"]
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Orders", f"{orders.order_id.nunique():,}")
k2.metric("Item revenue", f"R$ {filtered.price.sum():,.0f}")
k3.metric("Customers", f"{orders.customer_unique_id.nunique():,}")
k4.metric("Average review", f"{orders.review_score.mean():.2f} / 5")
k5.metric("Late delivery rate", f"{(delivered.delivery_status == 'Late').mean():.1%}")
st.caption(f"Showing {len(filtered):,} order items across {len(orders):,} orders.")

overview, geography, products, experience = st.tabs(
    ["Overview", "Geography", "Products", "Delivery & reviews"]
)

with overview:
    monthly = (
        filtered.assign(month=filtered.order_purchase_timestamp.dt.to_period("M").dt.to_timestamp())
        .groupby("month")
        .agg(orders=("order_id", "nunique"), revenue=("price", "sum"))
        .reset_index()
    )
    metric = st.radio("Monthly metric", ["Orders", "Revenue"], horizontal=True)
    y = metric.lower()
    st.plotly_chart(
        px.line(monthly, x="month", y=y, markers=True, labels={y: metric, "month": "Month"}),
        width="stretch",
    )
    left, right = st.columns(2)
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday = (
        orders.assign(weekday=orders.order_purchase_timestamp.dt.day_name())
        .groupby("weekday").order_id.nunique().reindex(weekday_order).reset_index(name="orders")
    )
    hourly = (
        orders.assign(hour=orders.order_purchase_timestamp.dt.hour)
        .groupby("hour").order_id.nunique().reindex(range(24), fill_value=0).reset_index(name="orders")
    )
    left.plotly_chart(px.bar(weekday, x="weekday", y="orders", title="Orders by weekday"), width="stretch")
    right.plotly_chart(px.line(hourly, x="hour", y="orders", markers=True, title="Orders by hour"), width="stretch")

with geography:
    geo_metric = st.radio("Compare states by", ["Orders", "Customers", "Revenue", "Late rate"], horizontal=True)
    grouped = filtered.groupby("customer_state").agg(
        Orders=("order_id", "nunique"), Customers=("customer_unique_id", "nunique"), Revenue=("price", "sum")
    )
    late = orders.groupby("customer_state").delivery_status.apply(lambda x: (x == "Late").mean()).mul(100)
    grouped["Late rate"] = late
    shown = grouped.reset_index().nlargest(15, geo_metric).sort_values(geo_metric)
    st.plotly_chart(
        px.bar(shown, x=geo_metric, y="customer_state", orientation="h", title=f"Top customer states by {geo_metric.lower()}"),
        width="stretch",
    )

with products:
    product_metric = st.radio("Rank categories by", ["Items", "Orders", "Revenue"], horizontal=True)
    category = filtered.groupby("product_category").agg(
        Items=("order_item_id", "count"), Orders=("order_id", "nunique"), Revenue=("price", "sum")
    ).reset_index()
    shown = category.nlargest(15, product_metric).sort_values(product_metric)
    st.plotly_chart(
        px.bar(shown, x=product_metric, y="product_category", orientation="h", title=f"Top categories by {product_metric.lower()}"),
        width="stretch",
    )
    st.dataframe(category.sort_values(product_metric, ascending=False), hide_index=True, width="stretch")

with experience:
    usable = orders.dropna(subset=["review_score", "delivery_days"])
    left, right = st.columns(2)
    score_delivery = usable.groupby("review_score", as_index=False).delivery_days.median()
    left.plotly_chart(
        px.bar(score_delivery, x="review_score", y="delivery_days", title="Median delivery days by review score"),
        width="stretch",
    )
    review_status = usable.groupby("delivery_status", as_index=False).review_score.mean()
    right.plotly_chart(
        px.bar(review_status, x="delivery_status", y="review_score", range_y=[0, 5], title="Average review by delivery status"),
        width="stretch",
    )
    sample = filtered.dropna(subset=["product_weight_g", "freight_value"]).sample(
        min(3000, filtered[["product_weight_g", "freight_value"]].dropna().shape[0]), random_state=42
    )
    st.plotly_chart(
        px.scatter(sample, x="product_weight_g", y="freight_value", color="product_category",
                   opacity=0.45, title="Product weight vs freight value (sample up to 3,000 items)"),
        width="stretch",
    )

with st.expander("Filtered data"):
    st.dataframe(filtered.head(1000), hide_index=True, width="stretch")
    st.download_button("Download filtered data", filtered.to_csv(index=False), "olist_filtered.csv", "text/csv")
