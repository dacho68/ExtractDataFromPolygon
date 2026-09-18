from dotenv import load_dotenv
import os
import requests
from datetime import date
import duckdb
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from massive import RESTClient

import pandas as pd

# Load variables from .env into environment
load_dotenv()


def load_to_duckdb(rows, fieldnames):
    db_path = os.getenv("DUCKDB_PATH", "data/trading.duckdb")
    con = duckdb.connect(db_path)
    try:
        con.execute("""
        CREATE TABLE IF NOT EXISTS STOCK_TICKERS (
            ticker VARCHAR,
            name VARCHAR,
            market VARCHAR,
            locale VARCHAR,
            primary_exchange VARCHAR,
            type VARCHAR,
            active BOOLEAN,
            currency_name VARCHAR,
            cik VARCHAR,
            composite_figi VARCHAR,
            share_class_figi VARCHAR,
            last_updated_utc TIMESTAMP WITH TIME ZONE,
            ds DATE
        );
        """)
        insert_query = f"INSERT INTO STOCK_TICKERS ({', '.join(n.upper() for n in fieldnames)}) VALUES ({', '.join(['?'] * len(fieldnames))})"
        data_to_insert = []
        for row in rows:
            data_to_insert.append([row.get(field, None) for field in fieldnames])
        try:
            con.executemany(insert_query, data_to_insert)
            print(f"Inserted {len(rows)} rows into STOCK_TICKERS table.")
        except Exception as e:
            print("DuckDB insert failed:", e)
            print("Query:", insert_query)
            print("First row sample:", data_to_insert[:3])
            raise
    finally:
        con.close()

port = os.getenv("PORT")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASS")
debug = os.getenv("DEBUG")
polygon_api_key = os.getenv("POLYGON_API_KEY")
massive_api_key = os.getenv("MASSIVE_API_KEY")

print("Port:", port)
print("User:", user)
print("Password:", password)
print("Debug:", debug)

"""
| multiplier | timespan | Resulting bar size |
| --- | --- | --- |
| 1 | minute | 1‑minute bars |
| 5 | minute | 5‑minute bars |
| 15 | minute | 15‑minute bars |
| 1 | hour | 1‑hour bars |
| 4 | hour | 4‑hour bars |
| 1 | day | Daily bars |
| 7 | day | Weekly bars (7‑day) |
"""

MASSIVE_BASE_URL = "https://api.massive.com/v3"


def _redact_url(url):
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    redacted = []
    for key, value in query:
        if key.lower() in {"apikey", "api_key", "token", "access_token"}:
            redacted.append((key, "***"))
        else:
            redacted.append((key, value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(redacted), parts.fragment))


def _get_json_or_raise(url, params=None):
    response = requests.get(url, params=params, timeout=30)
    safe_url = _redact_url(response.url)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body_preview = response.text[:300].replace("\n", " ")
        raise RuntimeError(
            f"HTTP {response.status_code} for {safe_url}. Body: {body_preview}"
        ) from exc

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        body_preview = response.text[:300].replace("\n", " ")
        content_type = response.headers.get("Content-Type", "")
        raise RuntimeError(
            f"Non-JSON response from {safe_url}. Content-Type: {content_type}. Body: {body_preview}"
        ) from exc


def get_quotes(ticker, limit=50000, order="asc"):
    url = f"https://api.massive.com/v3/quotes/{ticker}"
    params = {
        "limit": limit,
        "order": order,
        "sort": "timestamp",
        "apiKey": polygon_api_key
    }

    results = []
    while True:
        r = _get_json_or_raise(url, params=params)
        results.extend(r.get("results", []))

        next_url = r.get("next_url")
        if not next_url:
            break

        url = next_url
        params = {}

    return pd.DataFrame(results)

# df = get_quotes("AAPL")
# print(df.head())

def get_ohlc(ticker, start, end, multiplier=1, timespan="minute", limit=50000):
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": limit,
        "apiKey": polygon_api_key
    }

    url = f"{MASSIVE_BASE_URL}/quotes/{ticker}/range/{multiplier}/{timespan}/{start}/{end}"
    r = _get_json_or_raise(url, params=params)
    return pd.DataFrame(r.get("results", []))

def get_ohlc_v2(ticker, start_date, timespan="minute", limit=100):
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": limit,
        "apiKey": polygon_api_key
    }

    url = f"{MASSIVE_BASE_URL}/quotes/{ticker}?timespan={timespan}&start={start_date}&limit={limit}&apiKey={polygon_api_key}"
    r = _get_json_or_raise(url, params=params)
    return pd.DataFrame(r.get("results", []))


def save_df_to_csv(dataframe, filename, file_path):
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("'dataframe' must be a pandas DataFrame.")

    os.makedirs(file_path, exist_ok=True)
    output_path = os.path.join(file_path, filename)
    if not output_path.lower().endswith(".csv"):
        output_path += ".csv"

    dataframe.to_csv(output_path, index=False)
    print(f"Saved DataFrame to {output_path}")
    return output_path





client = RESTClient(massive_api_key)


aggs = []
for a in client.list_aggs(
    "AAPL",
    1,
    "minute",
    "2026-07-10",
    "2026-07-11",
    adjusted="true",
    sort="asc",
    limit=1000,
):
    aggs.append(a)

print(aggs)

# quotes = []
# for t in client.list_quotes(
# 	ticker="AAPL",
# 	order="asc",
# 	limit=10,
# 	sort="timestamp",
# 	):
#     quotes.append(t)

# print(quotes)

# df = get_ohlc_v2("AAPL", "2023-01-01")
# print(df.head())
# save_df_to_csv(df, "aapl_2023-01-01_2023-01-30", "data")



example_ticker = {'ticker': 'A', 
'name': 'Agilent Technologies Inc.', 
'market': 'stocks', 
'locale': 'us', 
'primary_exchange': 'XNYS', 
'type': 'CS', 
'active': True, 
'currency_name': 'usd', 
'cik': '0001090872', 
'composite_figi': 'BBG000C2V3D6', 
'share_class_figi': 'BBG001SCTQY4', 
'last_updated_utc': '2025-10-15T06:05:51.037116752Z',
'ds': '2025-10-15'}



# LIMIT = 1000

# url = f'https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}'
# response = requests.get(url)
