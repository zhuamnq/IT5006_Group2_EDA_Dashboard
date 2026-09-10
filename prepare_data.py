from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "IT5006_Project-Data" / "Olist_CSV"
OUT = Path(__file__).with_name("data") / "olist_dashboard.csv.gz"


def main():
    orders = pd.read_csv(RAW / "olist_orders_dataset.csv")
    customers = pd.read_csv(RAW / "olist_customers_dataset.csv")
    items = pd.read_csv(RAW / "olist_order_items_dataset.csv")
    products = pd.read_csv(RAW / "olist_products_dataset.csv")
    sellers = pd.read_csv(RAW / "olist_sellers_dataset.csv")
    translations = pd.read_csv(
        RAW / "product_category_name_translation.csv", encoding="utf-8-sig"
    )
    reviews = (
        pd.read_csv(RAW / "olist_order_reviews_dataset.csv")
        .groupby("order_id", as_index=False)["review_score"]
        .mean()
    )

    data = (
        items.merge(orders, on="order_id", how="left", validate="many_to_one")
        .merge(customers, on="customer_id", how="left", validate="many_to_one")
        .merge(products, on="product_id", how="left", validate="many_to_one")
        .merge(translations, on="product_category_name", how="left", validate="many_to_one")
        .merge(sellers, on="seller_id", how="left", validate="many_to_one")
        .merge(reviews, on="order_id", how="left", validate="many_to_one")
    )

    date_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for column in date_columns:
        data[column] = pd.to_datetime(data[column])

    data["delivery_days"] = (
        data["order_delivered_customer_date"] - data["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    data["delay_days"] = (
        data["order_delivered_customer_date"] - data["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400
    data["delivery_status"] = data["delay_days"].map(
        lambda value: "Unknown" if pd.isna(value) else ("Late" if value > 0 else "On time / early")
    )
    data["product_category"] = data["product_category_name_english"].fillna("Unknown")

    keep = [
        "order_id", "order_item_id", "product_id", "seller_id",
        "customer_unique_id", "order_status",
        "order_purchase_timestamp", "customer_state", "seller_state",
        "product_category", "price", "freight_value", "review_score",
        "product_weight_g", "product_length_cm", "product_height_cm",
        "product_width_cm", "delivery_days", "delay_days", "delivery_status",
    ]
    OUT.parent.mkdir(exist_ok=True)
    data[keep].to_csv(OUT, index=False, compression="gzip")
    print(f"Wrote {len(data):,} rows to {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
