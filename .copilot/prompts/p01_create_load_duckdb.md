# Goal

Create an equivalent function calls load_to_duckdb(rows, fieldnames) using the template code of snowflake, but the new load_to_duckdb if for duck db

## template code of snowflake
``` python
def load_to_snowflake(rows, fieldnames):
    # Build connection kwargs from environment variables
    connect_kwargs = {
        'user': os.getenv("SNOWFLAKE_USER"),
        'password': os.getenv("SNOWFLAKE_PASSWORD"),
    }
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    if account:
        connect_kwargs['account'] = account
    else:
        print("Note: SNOWFLAKE_ACCOUNT not set. If connection fails, set SNOWFLAKE_ACCOUNT in your .env (use value from your Snowflake URL).")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    database = os.getenv("SNOWFLAKE_DATABASE")
    schema = os.getenv("SNOWFLAKE_SCHEMA")
    role = os.getenv("SNOWFLAKE_ROLE")
    if warehouse:
        connect_kwargs['warehouse'] = warehouse
    if database:
        connect_kwargs['database'] = database
    if schema:
        connect_kwargs['schema'] = schema
    if role:
        connect_kwargs['role'] = role

    ctx = snowflake.connector.connect(**connect_kwargs)     
    cs = ctx.cursor()
    try:
        create_table_query = f"""
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
            last_updated_utc TIMESTAMP_NTZ,
            ds DATE
        );
        """
        cs.execute(create_table_query)
        insert_query = f"INSERT INTO STOCK_TICKERS ({', '.join(n.upper() for n in fieldnames)}) VALUES ({', '.join(['%s'] * len(fieldnames))})"
        data_to_insert = []
        for row in rows:
            data_to_insert.append([row.get(field, None) for field in fieldnames])
        try:
            cs.executemany(insert_query, data_to_insert)
            print(f"Inserted {len(rows)} rows into STOCK_TICKERS table.")
        except Exception as e:
            print("Snowflake insert failed:", e)
            print("Query:", insert_query)
            print("First row sample:", data_to_insert[:3])
            raise
    finally:
        cs.close()
        ctx.close()
```