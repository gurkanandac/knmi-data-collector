import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import requests
import xarray as xr
import pandas as pd
import mysql.connector
import os
logging.basicConfig(level=logging.INFO)


class OpenDataAPI:
    def __init__(self, api_token: str):
        self.base_url = "https://api.dataplatform.knmi.nl/open-data/v1"
        self.headers = {"Authorization": api_token}

    def __get_data(self, url, params=None):
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def list_files(self, dataset_name: str, dataset_version: str, params: dict):
        return self.__get_data(
            f"{self.base_url}/datasets/{dataset_name}/versions/{dataset_version}/files",
            params=params,
        )

    def get_file_url(self, dataset_name: str, dataset_version: str, file_name: str):
        return self.__get_data(
            f"{self.base_url}/datasets/{dataset_name}/versions/{dataset_version}/files/{file_name}/url"
        )


def get_secret_from_keyvault(secret_name: str) -> str:
    keyvault_name = "weather-keyvault-grk"
    kv_url = f"https://{keyvault_name}.vault.azure.net/"
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_url, credential=credential)
    secret = client.get_secret(secret_name)
    logging.info(f"Retrieved secret {secret_name} from Key Vault")
    return secret.value


def download_file(download_url: str, filename: str):
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f: 
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    logging.info(f"Downloaded file: {filename}")


def convert_nc_to_csv(nc_file: str, csv_file: str) -> pd.DataFrame:
    ds = xr.open_dataset(nc_file)
    df = ds.to_dataframe().reset_index()
    df.to_csv(csv_file, index=False)
    logging.info(f"Converted {nc_file} to CSV: {csv_file}")
    return df


def insert_dataframe_to_mysql(df: pd.DataFrame, table_name: str):
    # Get database credentials from Key Vault or environment variables
    conn = mysql.connector.connect(
        host=get_secret_from_keyvault("db-host"),
        user=get_secret_from_keyvault("db-username"),
        password=get_secret_from_keyvault("db-password"),
        database=get_secret_from_keyvault("db-name")
    )

    cursor = conn.cursor()
    # Rename problematic columns
    df = df.rename(columns=lambda x: x.replace("-", "_"))


    # Prepare column names and placeholders for MySQL
    columns = ", ".join(df.columns)
    placeholders = ", ".join(["%s"] * len(df.columns))
    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

        # Wrap all column names in backticks
    columns = ", ".join([f"`{col}`" for col in df.columns])
    placeholders = ", ".join(["%s"] * len(df.columns))
    sql = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders})"

    # Convert DataFrame to list of tuples, replacing NaN with None
    data = [tuple(None if pd.isna(x) else x for x in row) for row in df.to_numpy()]

    # Insert data
    try:
        cursor.executemany(sql, data)
        conn.commit()
        logging.info(f"Inserted {cursor.rowcount} rows into {table_name}")
    except mysql.connector.Error as err:
        logging.error(f"MySQL error: {err}")
    finally:
        cursor.close()
        conn.close()


def main(mytimer: func.TimerRequest) -> None:
    api_key = get_secret_from_keyvault("knmi-api-key")
    dataset_name = "Actuele10mindataKNMIstations"
    dataset_version = "2"
    params = {"maxKeys": 1, "orderBy": "created", "sorting": "desc"}

    api = OpenDataAPI(api_token=api_key)
    response = api.list_files(dataset_name, dataset_version, params)
    latest_file = response["files"][0]["filename"]
    logging.info(f"Latest file: {latest_file}")

    url_response = api.get_file_url(dataset_name, dataset_version, latest_file)
    download_url = url_response["temporaryDownloadUrl"]

    # Use /tmp for Azure Functions writable directory
    local_nc = os.path.join("/tmp", latest_file)
    local_csv = os.path.join("/tmp", latest_file.replace(".nc", ".csv"))

    # Download and convert
    download_file(download_url, local_nc)
    df = convert_nc_to_csv(local_nc, local_csv)

    # Insert into MySQL
    insert_dataframe_to_mysql(df, table_name="knmi_weather_data")

if __name__ == "__main__":
    main(None)