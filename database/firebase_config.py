"""
Firebase Admin & Client Configuration for FactoryFlow.
- Initializes firebase-admin (for Firestore & Auth Admin) using serviceAccountKey.json or .env.
- Provides fallback to local simulated memory store if Firebase credentials are not yet provided.
- Handles Firebase Web Auth REST API endpoint configuration.
"""

import os
import json

_firebase_admin_initialized = False
_db_instance = None
_firebase_auth_mode = "simulated"  # 'firebase' or 'simulated'


def get_firebase_credentials():
    """
    Attempts to locate Firebase credentials from:
    1. Local serviceAccountKey.json in root or path specified in .env (FIREBASE_SERVICE_ACCOUNT_PATH)
    2. Direct environment variables from .env / os.environ
    """
    # 1. Check serviceAccountKey.json path from .env / default
    sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "serviceAccountKey.json")
    if os.path.exists(sa_path):
        try:
            with open(sa_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Could not read {sa_path}: {e}")

    # 2. Check environment variables
    env_project_id = os.getenv("FIREBASE_PROJECT_ID")
    env_client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
    env_private_key = os.getenv("FIREBASE_PRIVATE_KEY")
    if env_project_id and env_client_email and env_private_key:
        return {
            "type": "service_account",
            "project_id": env_project_id,
            "client_email": env_client_email,
            "private_key": env_private_key.replace("\\n", "\n"),
        }

    return None


def get_firebase_web_api_key():
    """Returns Firebase Web API key from .env / os.environ."""
    return os.getenv("FIREBASE_WEB_API_KEY", "")


def initialize_firebase():
    """
    Initializes Firebase Admin SDK and Firestore client safely.
    Returns (db, mode) where mode is 'firebase' or 'simulated'.
    """
    global _firebase_admin_initialized, _db_instance, _firebase_auth_mode

    if _db_instance is not None:
        return _db_instance, _firebase_auth_mode

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        cred_dict = get_firebase_credentials()
        if cred_dict and cred_dict.get("project_id") != "factoryflow-demo":
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            _db_instance = firestore.client()
            _firebase_auth_mode = "firebase"
            _firebase_admin_initialized = True
            return _db_instance, _firebase_auth_mode

        adc_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if adc_path and os.path.exists(adc_path):
            if not firebase_admin._apps:
                cred = credentials.Certificate(adc_path)
                firebase_admin.initialize_app(cred)
            _db_instance = firestore.client()
            _firebase_auth_mode = "firebase"
            _firebase_admin_initialized = True
            return _db_instance, _firebase_auth_mode
    except Exception:
        pass

    _firebase_auth_mode = "simulated"
    return None, "simulated"
