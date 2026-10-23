from google.cloud import bigquery
import time
from pathlib import Path

import pandas as pd
import requests




PROJECT_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_DIR / "data"
POPULATION_FILE = DATA_DIR / "population.csv"
OUTPUT_FILE = DATA_DIR / "current_weather_stats.csv"

API_URL = "https://api.open-meteo.com/v1/forecast"




def fetch_weather(location):
    """Fetch current temperature and wind speed for a location."""

    params = {
        "latitude": location["Latitude"],
        "longitude": location["Longitude"],
        "current": "temperature_2m,wind_speed_10m",
        "timezone": "auto",
    }

    for attempt in range(1, 4):
        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=30,
            )
            response.raise_for_status()

            payload = response.json()
            current = payload.get("current")

            if not current:
                raise ValueError("Current weather data is missing.")

            return {
                "City": location["City"],
                "Country": location["Country"],
                "Temperature": current["temperature_2m"],
                "Wind_Speed": current["wind_speed_10m"],
                "Weather_Time": current["time"],
            }

        except requests.RequestException:
            if attempt == 3:
                raise

            print(
                f"Request failed for {location['City']}. "
                f"Retrying ({attempt}/3)..."
            )
            time.sleep(2)



def main():

    
    if not POPULATION_FILE.exists():
        raise FileNotFoundError(
            f"Population file not found: {POPULATION_FILE}"
        )

    # Load population data.
    population_df = pd.read_csv(POPULATION_FILE)

    required_columns = {
        "City",
        "Country",
        "Population",
        "Latitude",
        "Longitude",
    }

    missing_columns = required_columns - set(population_df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    print("Population dataset loaded successfully.")
    print("Population rows:", len(population_df))

   
    locations = population_df.head(50).copy()

    weather_records = []

    print("\nFetching current weather data...\n")

    for _, location in locations.iterrows():

        try:
            weather_record = fetch_weather(location)
            weather_records.append(weather_record)

            print(
                f"{weather_record['City']}, "
                f"{weather_record['Country']}: "
                f"{weather_record['Temperature']} °C"
            )

        except (requests.RequestException, ValueError, KeyError) as error:
            print(
                f"Could not fetch weather for "
                f"{location['City']}: {error}"
            )

        time.sleep(0.2)

    if not weather_records:
        raise RuntimeError(
            "No weather data was retrieved. Check your internet connection."
        )

    weather_df = pd.DataFrame(weather_records)

    merged_df = population_df.merge(
        weather_df,
        on=["City", "Country"],
        how="inner",
        validate="one_to_one",
    )

    print("\nRows after merging:", len(merged_df))

    for column in [
        "Population",
        "Latitude",
        "Longitude",
        "Temperature",
        "Wind_Speed",
    ]:
        merged_df[column] = pd.to_numeric(
            merged_df[column],
            errors="coerce",
        )

    merged_df = merged_df.dropna(
        subset=[
            "City",
            "Country",
            "Population",
            "Latitude",
            "Longitude",
            "Temperature",
            "Wind_Speed",
        ]
    ).copy()

    # Enforce required data types.
    merged_df["Population"] = merged_df["Population"].astype("int64")
    merged_df["Temperature"] = merged_df["Temperature"].astype("float64")
    merged_df["Wind_Speed"] = merged_df["Wind_Speed"].astype("float64")

    # Convert Celsius to Fahrenheit.
    merged_df["Temperature_Fahrenheit"] = (
        merged_df["Temperature"] * 9 / 5 + 32
    ).astype("float64")

    # Categorize temperatures:
    # Cold: <= 15°C
    # Mild: > 15°C and <= 25°C
    # Hot: > 25°C
    merged_df["Temperature_Category"] = pd.cut(
        merged_df["Temperature"],
        bins=[float("-inf"), 15, 25, float("inf")],
        labels=["Cold", "Mild", "Hot"],
        right=True,
    ).astype("string")

    # Save the final dataset.
    merged_df.to_csv(OUTPUT_FILE, index=False)

    print("\nPipeline completed successfully.")
    print("Rows in final dataset:", len(merged_df))
    print("Output file:", OUTPUT_FILE)

    print("\nData types:")
    print(merged_df.dtypes)

    print("\nFirst 10 rows:")
    print(merged_df.head(10).to_string(index=False))

    

    print("\nUploading data to BigQuery...")

    client = bigquery.Client.from_service_account_json(
        str(PROJECT_DIR / "scripts" / "gcp-key.json")
    )

    table_id = (
        "striped-buckeye-512500-d1."
        "global_weather_data.current_weather_stats"
    )

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )

    job = client.load_table_from_dataframe(
        merged_df,
        table_id,
        job_config=job_config,
    )

    job.result()

    print("Data uploaded successfully to BigQuery!")

    table = client.get_table(table_id)
    print("Rows in BigQuery table:", table.num_rows)

    return merged_df


if __name__ == "__main__":
    final_df = main()
