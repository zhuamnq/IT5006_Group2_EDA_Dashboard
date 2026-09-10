# Olist E-commerce Explorer

Interactive exploratory dashboard for IT5006 Milestone 1, built with Streamlit.

**Live app:** https://it5006-group2-dashboard.streamlit.app/

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The committed compressed dataset is derived from the public Olist dataset. To rebuild it from the course data folder:

```bash
python prepare_data.py
```

## Deploy

In Streamlit Community Cloud, select this repository and set the entry point to `app.py`.
