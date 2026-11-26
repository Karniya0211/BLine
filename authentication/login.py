"""
Authentication Service for FactoryFlow (Flask Compatible).
- Supports Firebase Auth REST API (email/password login and password reset).
- Handles fallback simulated auth mode for immediate zero-config testing.
- Includes pre-seeded accounts for all 5 roles:
  1. owner@factoryflow.com
  2. admin@factoryflow.com
  3. sales@factoryflow.com
  4. supervisor@factoryflow.com
  5. auditor@factoryflow.com
"""

import os
import requests
import smtplib
import secrets
from email.message import EmailMessage
from database.firebase_config import get_firebase_web_api_key, initialize_firebase
from authentication.permissions import (
    ROLE_OWNER,
    ROLE_ADMIN,
    ROLE_SALESMAN,
    ROLE_SUPERVISOR,
    ROLE_AUDITOR,
)
from utils.validators import validate_email

DEMO_USERS = {
    "owner@BLine.com": {
        "password": "Password123!",
        "name": "Karniya (Plant Owner)",
        "role": ROLE_OWNER,
        "uid": "usr_owner_01",
    },
    "admin@BLine.com": {
        "password": "Password123!",
        "name": "Ramesh Kumar",
        "role": ROLE_ADMIN,
        "uid": "usr_admin_02",
    },
    "sales@BLine.com": {
        "password": "Password123!",
        "name": "Suresh Murugan",
        "role": ROLE_SALESMAN,
        "uid": "usr_sales_03",
    },
    "supervisor@BLine.com": {
        "password": "Password123!",
        "name": "Palanisamy V.",
        "role": ROLE_SUPERVISOR,
        "uid": "usr_sup_04",
    },
    "auditor@BLine.com": {
        "password": "Password123!",
        "name": "Meenakshi Sundaram & Co.",
        "role": ROLE_AUDITOR,
        "uid": "usr_audit_05",
    },
    # Backward compatibility with existing credentials
    "owner@factoryflow.com": {
        "password": "Password123!",
        "name": "Karniya (Plant Owner)",
        "role": ROLE_OWNER,
        "uid": "usr_owner_01",
    },
    "admin@factoryflow.com": {
        "password": "Password123!",
        "name": "Ramesh Kumar",
        "role": ROLE_ADMIN,
        "uid": "usr_admin_02",
    },
    "sales@factoryflow.com": {
        "password": "Password123!",
        "name": "Suresh Murugan",
        "role": ROLE_SALESMAN,
        "uid": "usr_sales_03",
    },
    "supervisor@factoryflow.com": {
        "password": "Password123!",
        "name": "Palanisamy V.",
        "role": ROLE_SUPERVISOR,
        "uid": "usr_sup_04",
    },
    "auditor@factoryflow.com": {
        "password": "Password123!",
        "name": "Meenakshi Sundaram & Co.",
        "role": ROLE_AUDITOR,
        "uid": "usr_audit_05",
    },
}


def authenticate_with_firebase(email: str, password: str):
    api_key = get_firebase_web_api_key()
    if not api_key or api_key.startswith("AIzaSySample"):
        return None, "Firebase API Key not configured or using default."

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {"email": email, "password": password, "returnSecureToken": True}

    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if "error" in data:
            err_msg = data["error"].get("message", "Authentication failed.")
            if "EMAIL_NOT_FOUND" in err_msg or "INVALID_PASSWORD" in err_msg or "INVALID_LOGIN_CREDENTIALS" in err_msg:
                return None, "Invalid email address or password."
            return None, err_msg
        return data, None
    except Exception as e:
        return None, f"Network error during authentication: {str(e)}"


def reset_password_firebase(email: str):
    api_key = get_firebase_web_api_key()
    if not api_key or api_key.startswith("AIzaSySample"):
        return False, f"Password reset simulated: Recovery link dispatched to {email}"

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        if "error" in data:
            return False, data["error"].get("message", "Could not send reset email.")
        return True, "Password reset instructions dispatched to your email address."
    except Exception as e:
        return False, str(e)


def send_password_reset_code(email: str):
    """Send a short-lived recovery code through the configured SMTP relay."""
    host, sender = os.getenv("SMTP_HOST", "").strip(), os.getenv("SMTP_FROM", "").strip()
    if not host or not sender:
        return None, "Password recovery email is not configured. Set SMTP_HOST and SMTP_FROM."
    code = f"{secrets.randbelow(1_000_000):06d}"
    message = EmailMessage()
    message["Subject"], message["From"], message["To"] = "BLine password recovery code", sender, email
    message.set_content(f"Your BLine password recovery code is {code}. It expires in 10 minutes. Do not share it.")
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as server:
            if os.getenv("SMTP_USE_TLS", "true").lower() != "false":
                server.starttls()
            if os.getenv("SMTP_USERNAME", ""):
                server.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD", ""))
            server.send_message(message)
        return code, None
    except Exception:
        return None, "Unable to deliver the recovery code. Please contact your system administrator."


def set_password(email: str, new_password: str):
    normalized = email.lower()
    if normalized in DEMO_USERS:
        DEMO_USERS[normalized]["password"] = new_password
        return True, None
    try:
        from firebase_admin import auth
        user = auth.get_user_by_email(normalized)
        auth.update_user(user.uid, password=new_password)
        return True, None
    except Exception:
        return False, "Unable to update this account password."


def create_employee_auth(email: str, password: str, display_name: str):
    """Create a Firebase Authentication identity when the deployment is live.

    Simulated deployments retain the local credential path used by the demo.
    """
    db, mode = initialize_firebase()
    if mode != "firebase":
        return True, None
    try:
        from firebase_admin import auth
        user = auth.create_user(email=email, password=password, display_name=display_name)
        return True, user.uid
    except Exception:
        return False, "Unable to create the authentication account for this email address."


def get_user_profile_from_firestore(uid: str, email: str) -> dict:
    db, mode = initialize_firebase()
    if mode == "firebase" and db:
        try:
            doc = db.collection("users").document(uid).get()
            if doc.exists:
                return doc.to_dict()
        except Exception:
            pass

    # The local development datastore uses the same profile schema as Firestore.
    # Look up by email as Firebase and simulated identities can have different UIDs.
    try:
        from database.firestore_operations import get_users
        profile = next((u for u in get_users() if u.get("email", "").lower() == email.lower()), None)
        if profile:
            return profile
    except Exception:
        pass

    if email in DEMO_USERS:
        return {
            "name": DEMO_USERS[email]["name"],
            "role": DEMO_USERS[email]["role"],
            "email": email,
            "uid": DEMO_USERS[email]["uid"],
        }

    return {
        "name": email.split("@")[0].capitalize(),
        "role": ROLE_SALESMAN,
        "email": email,
        "uid": uid,
    }
