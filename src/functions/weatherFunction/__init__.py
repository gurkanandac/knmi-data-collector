import logging
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import requests

class OpenDataAPI:
    def __init__(self, api_token: str):
        self.base_url = "https://api.dataplatform.knmi.nl/open-data/v1"
        self.headers = {"Authorization": api_token}

    def __get_data(self, url, params=None):
        return requests.get(url, headers=self.headers, params=params).json()

    def list_files(self, dataset_name: str, dataset_version: str, params: dict):
        return self.__get_data(
            f"{self.base_url}/datasets/{dataset_name}/versions/{dataset_version}/files",
            params=params,
        )
    
def get_api_key_from_keyvault():
    keyvault_name = ""
    secret_name = ""
    kv_url = f"https://{keyvault_name}.vault.azure.net/"
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_url, credential=credential)
    secret = client.get_secret(secret_name)
    return secret.value

def main(mytimer: func.TimerRequest) -> None:
    api_key = get_api_key_from_keyvault
    dataset_name = "Actuele10mindataKNMIstations"
    dataset_version = "2"
    params = {"maxKeys": 1, "orderBy": "created", "sorting": "desc"}

    api = OpenDataAPI(api_token=api_key)
    response = api.list_files(dataset_name, dataset_version, params)
    logging.info(f"API response: {response}")