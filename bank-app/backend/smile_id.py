"""
smile_id.py — Smile Identity REST API v2 integration helper
Docs: https://docs.usesmileid.com/server-to-server/python
"""
import os
import json
import hashlib
import base64
import time
import hmac
import requests
from dotenv import load_dotenv

load_dotenv()

PARTNER_ID     = os.getenv("SMILE_PARTNER_ID", "")
API_KEY        = os.getenv("SMILE_API_KEY", "")
ENVIRONMENT    = os.getenv("SMILE_ENVIRONMENT", "sandbox")
THRESHOLD      = float(os.getenv("SMILE_CONFIDENCE_THRESHOLD", "0.7"))

BASE_URLS = {
    "sandbox":    "https://testapi.smileidentity.com/v1",
    "production": "https://api.smileidentity.com/v1",
}
BASE_URL = BASE_URLS.get(ENVIRONMENT, BASE_URLS["sandbox"])

# Supported ID types per country — expand as needed
ID_TYPES = {
    "KE": ["NATIONAL_ID", "PASSPORT", "ALIEN_CARD"],
    "NG": ["NIN", "BVN", "PASSPORT", "DRIVERS_LICENSE", "VOTER_ID"],
    "GH": ["VOTER_ID", "DRIVER_LICENSE", "SSNIT", "PASSPORT"],
    "ZA": ["NATIONAL_ID", "PASSPORT", "DRIVERS_LICENSE"],
    "UG": ["NATIONAL_ID", "PASSPORT"],
    "TZ": ["NATIONAL_ID", "PASSPORT"],
    "RW": ["NATIONAL_ID", "PASSPORT"],
}


def _generate_signature(timestamp: str) -> str:
    """HMAC-SHA256 signature required by Smile ID v1 API."""
    msg = f"{timestamp}{PARTNER_ID}sid_request"
    sig = hmac.new(API_KEY.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def _build_auth() -> dict:
    ts = str(int(time.time()))
    return {
        "partner_id": PARTNER_ID,
        "timestamp": ts,
        "signature": _generate_signature(ts),
    }


def is_configured() -> bool:
    """Returns True if Smile ID credentials are set."""
    return bool(PARTNER_ID and API_KEY and PARTNER_ID != "your_partner_id_here")


def verify_id_number(id_number: str, country: str = "KE", id_type: str = "NATIONAL_ID",
                     first_name: str = "", last_name: str = "") -> dict:
    """
    ID API Product — verify an ID number against the government database.
    Returns: { success, result_code, result_text, country, id_type, full_data }
    """
    if not is_configured():
        return {"success": False, "error": "Smile ID not configured", "mock": True}

    payload = {
        **_build_auth(),
        "country": country,
        "id_type": id_type,
        "id_number": id_number,
        "first_name": first_name,
        "last_name": last_name,
        "partner_params": {
            "job_id": f"job_{int(time.time())}",
            "user_id": f"user_{id_number[:8]}",
            "job_type": 5,  # Enhanced KYC
        },
    }

    try:
        resp = requests.post(f"{BASE_URL}/id_verification", json=payload, timeout=30)
        data = resp.json()
        result_code = data.get("result", {}).get("ResultCode", "")
        result_text = data.get("result", {}).get("ResultText", "")
        # 1012 = Exact match, 1013 = Partial match
        success = result_code in ("1012", "1013")
        return {
            "success": success,
            "result_code": result_code,
            "result_text": result_text,
            "country": country,
            "id_type": id_type,
            "full_data": data,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_biometric_kyc(id_number: str, selfie_b64: str, id_doc_b64: str,
                          country: str = "KE", id_type: str = "NATIONAL_ID",
                          first_name: str = "", last_name: str = "") -> dict:
    """
    Biometric KYC (Job Type 1) — smile liveness + ID doc + selfie face match.
    Returns: { success, confidence, result_code, result_text, actions, full_data }
    """
    if not is_configured():
        return {"success": False, "error": "Smile ID not configured", "mock": True}

    # Strip data URL prefix if present
    def strip_prefix(b64str):
        if b64str and "," in b64str:
            return b64str.split(",")[1]
        return b64str or ""

    selfie_clean  = strip_prefix(selfie_b64)
    id_doc_clean  = strip_prefix(id_doc_b64)

    payload = {
        **_build_auth(),
        "images": [
            {"image_type_id": 2, "image": selfie_clean},   # selfie
            {"image_type_id": 1, "image": id_doc_clean},   # ID front
        ],
        "id_info": {
            "country": country,
            "id_type": id_type,
            "id_number": id_number,
            "first_name": first_name,
            "last_name": last_name,
            "entered": "true",
        },
        "partner_params": {
            "job_id": f"bio_{int(time.time())}",
            "user_id": f"user_{id_number[:8]}",
            "job_type": 1,  # Biometric KYC
        },
        "options": {
            "return_job_status": True,
            "return_history": False,
            "return_images": False,
        },
    }

    try:
        resp = requests.post(f"{BASE_URL}/submission", json=payload, timeout=60)
        data = resp.json()
        job_result  = data.get("result", {})
        result_code = job_result.get("ResultCode", "")
        result_text = job_result.get("ResultText", "")
        actions     = job_result.get("Actions", {})
        confidence  = float(job_result.get("ConfidenceValue", 0))

        # 0810 = Provisional Approved, 0811 = Approved
        success = result_code in ("0810", "0811") and confidence >= (THRESHOLD * 100)
        return {
            "success": success,
            "confidence": confidence,
            "result_code": result_code,
            "result_text": result_text,
            "actions": actions,
            "full_data": data,
        }
    except Exception as e:
        return {"success": False, "confidence": 0, "error": str(e)}


def get_supported_id_types(country: str = None) -> dict:
    """Returns supported ID types, optionally filtered by country."""
    if country:
        return {country: ID_TYPES.get(country.upper(), [])}
    return ID_TYPES
