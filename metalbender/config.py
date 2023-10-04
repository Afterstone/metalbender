import os
from functools import lru_cache
from pathlib import Path

import dotenv
from google.cloud import secretmanager

dotenv.load_dotenv()


@lru_cache(maxsize=128)
def _access_secret_version(resource_name: str, decode: bool = True, encoding: str = "UTF-8") -> str | bytes:
    """
    Access the payload of the given secret version if one exists.

    :param name: The name of the secret version to access.

    :return: The payload of the secret version.
    """

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    response = client.access_secret_version(name=resource_name)

    # Return the decoded payload of the secret version.
    payload_data = response.payload.data
    return payload_data if not decode else payload_data.decode(encoding)


def clear_access_secret_version_cache() -> None:
    _access_secret_version.cache_clear()


def _get_envvar_str(envvar_name: str) -> str:
    project = os.getenv(envvar_name, None)
    if project is None:
        raise ValueError(f"{envvar_name} is not set")
    return project


def _get_envvar_list(envvar_name: str) -> list[str]:
    project = os.getenv(envvar_name, None)
    if project is None:
        raise ValueError(f"{envvar_name} is not set")
    return project.split(",")


def _get_envvar_path(envvar_name: str, check_exists: bool = True) -> Path:
    path_str = _get_envvar_str(envvar_name)
    try:
        path = Path(path_str)
    except Exception as e:
        raise ValueError(
            f"{envvar_name} is not a valid path: {path_str}") from e

    if check_exists and not path.exists():
        raise FileNotFoundError(f"{envvar_name} does not exist at path {path}")

    return path


def _get_secret_manager_file(
    secret_manager_resource_name: str,
    file_path: Path,
) -> Path:
    file_contents = _access_secret_version(
        secret_manager_resource_name, decode=False)

    if not isinstance(file_contents, bytes):
        raise TypeError(f"Expected bytes, got {type(file_contents)}")

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_contents)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Failed to write secret manager file to {file_path}")

        file_path.chmod(0o600)
    except FileNotFoundError as fnfe:
        raise fnfe

    return file_path


def get_gcp_project_id() -> str:
    return _get_envvar_str("GCP_PROJECT_ID")


def get_gcp_gce_zones() -> list[str]:
    return _get_envvar_list("GCP_GCE_ZONES")


def get_fastapi_host() -> str:
    return _get_envvar_str("FASTAPI_HOST")


def get_fastapi_port() -> int:
    return int(_get_envvar_str("FASTAPI_PORT"))


def get_fastapi_username() -> str:
    return _get_envvar_str("FASTAPI_USERNAME")


def get_fastapi_password() -> str:
    return _get_envvar_str("FASTAPI_PASSWORD")


def get_sql_client_key_path() -> Path:
    return _get_secret_manager_file(
        _get_envvar_str("SQL_CLIENT_KEY_SECRETS_MANAGER_NAME"),
        Path('/tmp/sql_client_key.pem')
    )


def get_sql_server_ca_path() -> Path:
    return _get_secret_manager_file(
        _get_envvar_str("SQL_SERVER_CA_SECRETS_MANAGER_NAME"),
        Path('/tmp/sql_server_ca.pem')
    )


def get_sql_client_cert_path() -> Path:
    return _get_secret_manager_file(
        _get_envvar_str("SQL_CLIENT_CERT_SECRETS_MANAGER_NAME"),
        Path('/tmp/sql_client_cert.pem')
    )


def get_sql_database() -> str:
    return _get_envvar_str("SQL_DATABASE")


def get_sql_host() -> str:
    return _get_envvar_str("SQL_HOST")


def get_sql_password() -> str:
    password = _access_secret_version(
        _get_envvar_str("SQL_PASSWORD_SECRETS_MANAGER_NAME"))
    if not isinstance(password, str):
        raise TypeError(f"Expected str, got {type(password)}")
    return password


def get_sql_port() -> int:
    return int(_get_envvar_str("SQL_PORT"))


def get_sql_username() -> str:
    return _get_envvar_str("SQL_USERNAME")


def get_database_url() -> str:
    DATABASE_URL = (
        f"postgresql://{get_sql_username()}:{get_sql_password()}"
        f"@{get_sql_host()}:{get_sql_port()}/{get_sql_database()}"
    )

    return DATABASE_URL
