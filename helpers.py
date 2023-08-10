import json
import logging
import sys
import requests

from config import CONFIG

logger = logging.getLogger(__name__)


def get_ebuilder_token() -> str:
    url = f"{CONFIG['EB_API_BASE_URL']}/Authenticate"
    payload = (
        f"grant_type=password&username={CONFIG['EB_API_USERNAME']}&password={CONFIG['EB_API_PASSWORD']}"
    )
    payload = payload.replace("@", "%40")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code != 200:
        logger.error("Error refreshing token")
        sys.exit(1)
    return json.loads(response.text)["access_token"]
