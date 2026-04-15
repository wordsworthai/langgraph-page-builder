# secret_manager_util.py - Updated version matching get_connection.py pattern

from google.cloud import secretmanager
from typing import Optional
from wwai_agent_orchestration.core.observability.logger import get_logger
import os

# Configure logging
logger = get_logger(__name__)

def get_secret(secret_name: str, project_id: str = os.environ.get("GCP_PROJECT_ID", "")) -> str:
    """Get secret from Google Cloud Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to get secret {secret_name}: {str(e)}")
        raise ValueError(f"Failed to get secret {secret_name}: {str(e)}")

def get_secret_safe(secret_name: str, project_id: str = os.environ.get("GCP_PROJECT_ID", ""), version: str = "latest", default_value: Optional[str] = None) -> Optional[str]:
    """
    Safely retrieve a secret with optional default value.
    """
    try:
        return get_secret(secret_name, project_id)
    except Exception as e:
        logger.warning(f"⚠️ Failed to retrieve secret '{secret_name}', using default: {e}")
        return default_value

def check_secret_exists(secret_name: str, project_id: str = os.environ.get("GCP_PROJECT_ID", "")) -> bool:
    """Check if a secret exists in Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}"
        client.get_secret(request={"name": name})
        return True
    except Exception:
        return False

def list_secrets(project_id: str = os.environ.get("GCP_PROJECT_ID", "")) -> list:
    """List all secrets in the project."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}"
        secrets = client.list_secrets(request={"parent": parent})
        secret_names = [secret.name.split('/')[-1] for secret in secrets]
        logger.info(f"✅ Found {len(secret_names)} secrets in project")
        return secret_names
    except Exception as e:
        logger.error(f"❌ Error listing secrets: {e}")
        return []

class SecretManagerHelper:
    """Helper class to manage Google Cloud Secret Manager operations."""

    def __init__(self, project_id: str = os.environ.get("GCP_PROJECT_ID", "")):
        self.project_id = project_id
        self._secret_client = None
        logger.info(f"✅ SecretManagerHelper initialized for project: {project_id}")

    @property
    def secret_client(self):
        if self._secret_client is None:
            self._secret_client = secretmanager.SecretManagerServiceClient()
        return self._secret_client

    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"❌ Error retrieving secret '{secret_name}': {e}")
            raise

    def get_secret_safe(self, secret_name: str, version: str = "latest", default_value: Optional[str] = None) -> Optional[str]:
        try:
            return self.get_secret(secret_name, version)
        except Exception as e:
            logger.warning(f"⚠️ Failed to retrieve secret '{secret_name}', using default: {e}")
            return default_value

    def check_secret_exists(self, secret_name: str) -> bool:
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}"
            self.secret_client.get_secret(request={"name": name})
            return True
        except Exception:
            return False

    def list_secrets(self) -> list:
        try:
            parent = f"projects/{self.project_id}"
            secrets = self.secret_client.list_secrets(request={"parent": parent})
            return [secret.name.split('/')[-1] for secret in secrets]
        except Exception as e:
            logger.error(f"❌ Error listing secrets: {e}")
            return []

def create_secret_manager(project_id: str = os.environ.get("GCP_PROJECT_ID", "")):
    return SecretManagerHelper(project_id)

def get_secret_manager_instance(project_id: str = os.environ.get("GCP_PROJECT_ID", "")):
    environment = os.getenv('ENVIRONMENT', 'local').lower()
    if environment == 'local':
        logger.info("Local environment detected, Secret Manager not initialized")
        return None
    return SecretManagerHelper(project_id)

secret_manager = None

def get_secret_manager():
    global secret_manager
    if secret_manager is None:
        secret_manager = get_secret_manager_instance()
    return secret_manager
