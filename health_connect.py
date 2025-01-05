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
	print(f"Fetching data for method: {method}")
	url = f"{BASE_URL}/{method}"
	headers = {
		"Authorization": f"Bearer {token}",
		"Content-Type": "application/json",
	}
	print(f"Request URL: {url}")
	print(f"Request Headers: {headers}")
	print(f"Request Body: {query_body}")

	# Make the request
	response = requests.post(url, headers=headers, data=json.dumps(query_body))
	print(f"Response Status Code: {response.status_code}")
	response.raise_for_status()  # Raise an error if the request failed

	# The response might be a single object or a list of objects—depends on actual API
	# Let's assume it's a list of documents. If it's a single doc, we adapt accordingly.
	data = response.json()
    
	# If the API returns a single object, wrap it in a list for convenience
	print(f"Fetched Data: {data}")

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
	
	print(f"DataFrame created with {len(df)} records.")
    
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
	print(f"Checking if table '{table_name}' exists in DuckDB.")
	create_table_sql = f"""
		CREATE TABLE IF NOT EXISTS {table_name} (
			_id TEXT PRIMARY KEY,
			data TEXT,
			id TEXT,
			start TIMESTAMP,
			"end" TIMESTAMP,
			app TEXT,
			method TEXT
		);
	"""
	con.execute(create_table_sql)
	print(f"Table '{table_name}' ensured in DuckDB.")


def save_to_duckdb(df: pd.DataFrame, db_path: str = DUCKDB_PATH, table_name: str = TABLE_NAME):
	print(f"Saving data to DuckDB at path: {db_path}")
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
	print(f"Temporary table 'temp_df' registered with {len(df)} records.")

	# Upsert! If the row with this _id exists, update the other columns with new values
	insert_sql = f"""
		INSERT INTO {table_name} (_id, data, id, start, "end", app, method)
		SELECT _id, data, id, start, "end", app, method
		FROM temp_df
		ON CONFLICT (_id) DO UPDATE SET
			data = EXCLUDED.data,
			id = EXCLUDED.id,
			start = EXCLUDED.start,
			"end" = EXCLUDED."end",
			app = EXCLUDED.app,
			method = EXCLUDED.method
	"""
	con.execute(insert_sql)
	print(f"Upserted records into '{table_name}'.")

	# Cleanup
	con.unregister("temp_df")
	con.close()
	print("Connection to DuckDB closed.")

def fetch_and_save_data(method: str):
	print(f"Starting data fetch and save process for method: {method}")
    
	# 1. Fetch data
	df = fetch_data(method, AUTH_TOKEN, QUERY)
	if df.empty:
		print(f"No data fetched for method='{method}'.")
		return

	# 2. Append only new rows to DuckDB
	save_to_duckdb(df, table_name=method)
	print(f"Inserted new rows for method '{method}' (if any) into DuckDB.")


def main():
	methods = [
		"activeCaloriesBurned", "basalBodyTemperature", "basalMetabolicRate", 
		"bloodGlucose", "bloodPressure", "bodyFat", "bodyTemperature", 
		"boneMass", "cervicalMucus", "distance", "exerciseSession", 
		"elevationGained", "floorsClimbed", "heartRate", "height", 
		"hydration", "leanBodyMass", "menstruationFlow", "menstruationPeriod", 
		"nutrition", "ovulationTest", "oxygenSaturation", "power", 
		"respiratoryRate", "restingHeartRate", "sleepSession", "speed", 
		"steps", "stepsCadence", "totalCaloriesBurned", "vo2Max", "weight", 
		"wheelchairPushes"
	]

	for method in methods:
		fetch_and_save_data(method)

if __name__ == "__main__":
	main()
