import typing

import requests
import edn_format

from . import edn_syntax


def get_symphony(symphony_id: str) -> dict:
    composerConfig = {
        "projectId": "leverheads-278521",
        "databaseName": "(default)"
    }
    print(f"Fetching symphony {symphony_id} from Composer")
    response = requests.get(
        f'https://firestore.googleapis.com/v1/projects/{composerConfig["projectId"]}/databases/{composerConfig["databaseName"]}/documents/symphony/{symphony_id}')
    response.raise_for_status()

    response_json = response.json()
    return response_json


def extract_root_node_from_symphony_response(response: dict) -> dict:
    return typing.cast(dict, edn_syntax.convert_edn_to_pythonic(
        edn_format.loads(response['fields']['latest_version_edn']['stringValue'])))
