import dotenv
from os import environ

dotenv.load_dotenv()
CONFIG = {
    'USER_EMAIL_ADDRESS': environ.get("EMAIL"),
    'EB_API_BASE_URL': environ.get("EB_API_BASE_URL"),
    'EB_API_USERNAME': environ.get("EB_API_USERNAME"),
    'EB_API_PASSWORD': environ.get("EB_API_PASSWORD"),
    'MUNIS_API_TOKEN_URL': environ.get("MUNIS_API_TOKEN_URL"),
    'MUNIS_API_CLIENT_ID': environ.get("MUNIS_API_CLIENT_ID"),
    'MUNIS_API_CLIENT_SECRET': environ.get("MUNIS_API_CLIENT_SECRET"),
    'MUNIS_API_SCOPES': environ.get("MUNIS_API_SCOPES"),
    'MUNIS_API_BASE_URL': environ.get("MUNIS_API_BASE_URL"),
    # Munis db connection string
    'MUNIS_DB_USER': environ.get("MUNIS_DB_USER"),
    'MUNIS_DB_PASSWORD': environ.get("MUNIS_DB_PASSWORD"),
    # email log errors
    'LOGGER_EMAIL': environ.get("LOGGER_EMAIL"),
    'LOGGER_PASS': environ.get("LOGGER_PASS"),
    'ENVIRONMENT': environ.get("ENVIRONMENT"),
    # set these to only run the api you are working on in development or to disable in production
    'COMMITMENTS_ENABLED': environ.get("COMMITMENTS_ENABLED", 'False').lower() in ('true', '1', 't'),
    'COMMITMENT_INVOICES_ENABLED': environ.get("COMMITMENT_INVOICES_ENABLED", 'False').lower() in ('true', '1', 't'),
    'COMMITMENT_INVOICES_SAVE_LOCATION': environ.get("COMMITMENT_INVOICES_SAVE_LOCATION"),
    'COMMITMENT_UPDATES_SAVE_LOCATION': environ.get("COMMITMENT_UPDATES_SAVE_LOCATION"),
}
