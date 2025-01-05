import os
import json
import requests
import duckdb
import pandas as pd
from datetime import datetime

# -------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------
# The base URL for the Health Connect Gateway
BASE_URL = "https://api.hcgateway.shuchir.dev/api/v2/fetch"

# Your Bearer token
AUTH_TOKEN = os.getenv("HC_BEARER_TOKEN", "REMOVED_HC_BEARER_TOKEN")

# Where we store our DuckDB file
DUCKDB_PATH = "health_connect.duckdb"

# The table name in DuckDB
TABLE_NAME = "health_data"

# The "method" you want to fetch (e.g. "heartRate", "steps", "weight", etc.)
METHOD = "sleepSession"

# You can adapt the queries object here to filter your data
QUERY = {
	"queries": {
		# e.g., "start": {"$gte": "2025-01-01T00:00:00Z"}
		# Just an empty filter in this example
	}
}


def fetch_data(method: str, token: str, query_body: dict) -> pd.DataFrame:
	"""
	POST /api/v2/fetch/{method} with a JSON body containing "queries".
	Returns a Pandas DataFrame containing the fetched data.
	"""
	url = f"{BASE_URL}/{METHOD}"
	headers = {
		"Authorization": f"Bearer {AUTH_TOKEN}",
		"Content-Type": "application/json",
	}

	# Make the request
	response = requests.post(url, headers=headers, data=json.dumps(query_body))
	response.raise_for_status()  # Raise an error if the request failed

	# The response might be a single object or a list of objects—depends on actual API
	# Let's assume it's a list of documents. If it's a single doc, we adapt accordingly.
	data = response.json()
    
	# If the API returns a single object, wrap it in a list for convenience
	if isinstance(data, dict):
		# Check if it's an object that should be in a list
		# If you know for sure the API always returns a list, remove this logic
		data = [data]

	# Convert to DataFrame
	# The typical structure could have columns:
	#   _id, data, id, start, end, app
	# We'll keep them as-is, plus store the method so we know which dataset it came from
	for record in data:
		record["method"] = method

	df = pd.DataFrame(data)
	
	#print(df)
	
	return df


def create_duckdb_table_if_needed(con, table_name: str):
	"""
	Create the 'health_data' table in DuckDB if it does not exist.
	We'll store:
	  - _id (TEXT) as the primary unique field
	  - data (JSON) or TEXT
	  - id (TEXT)
	  - start (TIMESTAMP)
	  - end (TIMESTAMP)
	  - app (TEXT)
	  - method (TEXT)
	Adjust as needed based on how you want to store it.
	"""
	create_table_sql = f"""
		CREATE TABLE IF NOT EXISTS {table_name} (
			_id TEXT,
			data TEXT,
			id TEXT,
			start TIMESTAMP,
			end TIMESTAMP,
			app TEXT,
			method TEXT
		);
	"""
	con.execute(create_table_sql)


def save_to_duckdb(df: pd.DataFrame, db_path: str = DUCKDB_PATH, table_name: str = TABLE_NAME):
	"""
	Insert data into DuckDB, skipping rows that have the same _id.
	"""
	# Connect
	con = duckdb.connect(db_path)

	# Ensure table exists
	create_duckdb_table_if_needed(con, table_name)

	# If your 'data' field is a dict, you might want to convert it to JSON string for storage
	if "data" in df.columns and df["data"].map(lambda x: isinstance(x, dict)).any():
		df["data"] = df["data"].apply(json.dumps)

	# If you want to parse 'start'/'end' as timestamps
	for col in ["start", "end"]:
		if col in df.columns:
			df[col] = pd.to_datetime(df[col], errors="coerce")

	# Register the new data as a temp table in DuckDB
	con.register("temp_df", df)

	# Make sure the columns match the target table's columns
	# We'll project them in the SELECT to be safe
	# (Any extra columns in df will be ignored)
	insert_sql = f"""
		INSERT INTO {table_name}
		SELECT
			_id,
			data,
			id,
			start,
			end,
			app,
			method
		FROM temp_df t
		LEFT JOIN {table_name} h
			ON t._id = h._id
		WHERE h._id IS NULL
	"""
	con.execute(insert_sql)

	# Cleanup
	con.unregister("temp_df")
	con.close()


def main():
	# 1. Fetch data
	df = fetch_data(METHOD, AUTH_TOKEN, QUERY)
	if df.empty:
		print(f"No data fetched for method='{METHOD}'.")
		return

	# 2. Append only new rows to DuckDB
	save_to_duckdb(df)

	print(f"Inserted new rows for method '{METHOD}' (if any) into DuckDB.")


if __name__ == "__main__":
	main()
