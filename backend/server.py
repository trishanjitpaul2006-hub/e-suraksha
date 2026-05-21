import json
import os
import random
import time
import uuid
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
OTP_EXPIRY_SECONDS = 300
OTP_STORE = {}
SOS_COOLDOWN_SECONDS = int(os.environ.get("SOS_COOLDOWN_SECONDS", "60"))
SOS_COOLDOWN_STORE = {}
SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "msg91").strip().lower()
MSG91_AUTH_KEY = os.environ.get("MSG91_AUTH_KEY", "")
MSG91_SENDER_ID = os.environ.get("MSG91_SENDER_ID", "ESURAK")
MSG91_ROUTE = os.environ.get("MSG91_ROUTE", "4")
MSG91_COUNTRY = os.environ.get("MSG91_COUNTRY", "91")
MSG91_SEND_URL = "https://api.msg91.com/api/sendhttp.php"
FAST2SMS_API_KEY = os.environ.get("FAST2SMS_API_KEY", "")
FAST2SMS_SEND_URL = "https://www.fast2sms.com/dev/bulkV2"


def ensure_data_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps({"users": []}, indent=2), encoding="utf-8")


def read_users():
    ensure_data_files()
    try:
        payload = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        users = payload.get("users", [])
        return users if isinstance(users, list) else []
    except Exception:
        return []


def write_users(users):
    ensure_data_files()
    USERS_FILE.write_text(json.dumps({"users": users}, indent=2), encoding="utf-8")


def json_response(status_code, payload):
    response = jsonify(payload)
    response.status_code = status_code
    return response


def normalize_phone(phone):
    return "".join(ch for ch in str(phone or "") if ch.isdigit())


def normalize_user_id(user_id):
    return str(user_id or "").strip().lower()


def is_valid_phone(phone):
    return len(phone) == 10 and phone.isdigit()


def mask_phone(phone):
    return f"{phone[:2]}******{phone[-2:]}"


def is_valid_msg91_phone(phone):
    return len(phone) == 12 and phone.isdigit() and phone.startswith("91")


def normalize_msg91_phone(phone):
    digits = normalize_phone(phone)
    if len(digits) == 10:
        return f"91{digits}"
    return digits


def build_sos_message(lat_value, lng_value):
    maps_link = f"https://maps.google.com/?q={lat_value:.6f},{lng_value:.6f}"
    return (
        "SOS ALERT - E-SURAKSHA\n\n"
        "Emergency assistance needed.\n\n"
        "Current Location:\n"
        f"Latitude: {lat_value:.6f}\n"
        f"Longitude: {lng_value:.6f}\n\n"
        "Google Maps:\n"
        f"{maps_link}"
    )


def get_sos_cooldown_key(phone, client_id=""):
    normalized_phone = normalize_msg91_phone(phone)
    normalized_client = str(client_id or "").strip()
    remote_addr = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    return normalized_phone or normalized_client or remote_addr or "anonymous"


def get_sos_cooldown_remaining(key):
    last_sent_at = SOS_COOLDOWN_STORE.get(key)
    if not last_sent_at:
        return 0
    elapsed = time.time() - last_sent_at
    remaining = SOS_COOLDOWN_SECONDS - elapsed
    return max(0, int(remaining + 0.999))


def send_msg91_sms(phone, message):
    if not MSG91_AUTH_KEY:
        raise RuntimeError("MSG91_AUTH_KEY is not configured.")
    if len(MSG91_SENDER_ID) != 6:
        raise RuntimeError("MSG91_SENDER_ID must be exactly 6 characters.")
    params = {
        "authkey": MSG91_AUTH_KEY,
        "mobiles": phone,
        "message": message,
        "sender": MSG91_SENDER_ID,
        "route": MSG91_ROUTE,
        "country": MSG91_COUNTRY,
    }
    response = requests.get(MSG91_SEND_URL, params=params, timeout=15)
    response.raise_for_status()
    return (response.text or "").strip()


def send_fast2sms_sms(phone, message):
    if not FAST2SMS_API_KEY:
        raise RuntimeError("FAST2SMS_API_KEY is not configured.")
    numbers = normalize_phone(phone)
    if numbers.startswith("91") and len(numbers) == 12:
        numbers = numbers[2:]
    payload = {
        "route": "q",
        "message": message,
        "numbers": numbers,
    }
    response = requests.post(
        FAST2SMS_SEND_URL,
        headers={
            "authorization": FAST2SMS_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return (response.text or "").strip()


def send_sms(phone, message):
    if SMS_PROVIDER == "fast2sms":
        return "fast2sms", send_fast2sms_sms(phone, message)
    if SMS_PROVIDER == "msg91":
        return "msg91", send_msg91_sms(phone, message)
    raise RuntimeError("SMS_PROVIDER must be msg91 or fast2sms.")


def validate_sos_payload(body):
    phone = normalize_msg91_phone(body.get("phone") or body.get("emergencyPhone") or "")
    lat = body.get("lat")
    lng = body.get("lng")

    if not is_valid_msg91_phone(phone):
        return None, json_response(400, {"success": False, "message": "Phone number must be in 91XXXXXXXXXX format."})
    try:
        lat_value = float(lat)
        lng_value = float(lng)
    except (TypeError, ValueError):
        return None, json_response(400, {"success": False, "message": "Latitude and longitude must be valid numbers."})
    if not (-90 <= lat_value <= 90) or not (-180 <= lng_value <= 180):
        return None, json_response(400, {"success": False, "message": "Latitude or longitude is outside the valid range."})
    return {"phone": phone, "lat": lat_value, "lng": lng_value}, None


def generate_otp():
    return f"{random.randint(100000, 999999)}"


def cleanup_expired_otps():
    now = time.time()
    expired = [key for key, value in OTP_STORE.items() if value["expires_at"] <= now]
    for key in expired:
        OTP_STORE.pop(key, None)


def create_otp_record(flow, payload):
    cleanup_expired_otps()
    otp_request_id = str(uuid.uuid4())
    otp = generate_otp()
    OTP_STORE[otp_request_id] = {
        "flow": flow,
        "payload": payload,
        "otp": otp,
        "expires_at": time.time() + OTP_EXPIRY_SECONDS,
        "attempts_left": 3,
    }

    print(f"[REQUEST RECEIVED] flow={flow}")
    print(f"Payload: {payload}")
    print(f"[DEMO OTP] {otp}")
    print("Use this OTP in the website form.\n")

    return {
        "otpRequestId": otp_request_id,
        "expiresInSeconds": OTP_EXPIRY_SECONDS,
        "maskedPhoneNumber": mask_phone(payload["phoneNumber"]),
    }


def build_public_user(user):
    return {
        "id": user.get("id", ""),
        "name": user.get("fullName", ""),
        "userId": user.get("userId", ""),
        "phoneNumber": user.get("phoneNumber", ""),
        "provider": "otp",
    }


def find_user_by_identifier(identifier):
    users = read_users()
    cleaned = str(identifier or "").strip()

    if cleaned.isdigit():
        phone = normalize_phone(cleaned)
        return next((user for user in users if user.get("phoneNumber") == phone), None)

    normalized_id = normalize_user_id(cleaned)
    return next((user for user in users if user.get("userIdNormalized") == normalized_id), None)


def verify_otp_record(otp_request_id, otp):
    cleanup_expired_otps()

    if not otp_request_id or not otp:
        return None, json_response(400, {"success": False, "message": "OTP request ID and OTP are required."})

    record = OTP_STORE.get(otp_request_id)
    if not record:
        return None, json_response(400, {"success": False, "message": "OTP expired or request not found. Please request a new OTP."})

    if record["expires_at"] <= time.time():
        OTP_STORE.pop(otp_request_id, None)
        return None, json_response(400, {"success": False, "message": "OTP expired. Please request a new OTP."})

    if str(record["otp"]) != str(otp):
        record["attempts_left"] -= 1
        if record["attempts_left"] <= 0:
            OTP_STORE.pop(otp_request_id, None)
            return None, json_response(400, {"success": False, "message": "Wrong OTP. Too many failed attempts. Please request a new OTP."})
        return None, json_response(400, {"success": False, "message": f"Wrong OTP. {record['attempts_left']} attempt(s) left."})

    OTP_STORE.pop(otp_request_id, None)
    return record, None


@app.route("/send-register-otp", methods=["POST"])
def send_register_otp():
    body = request.get_json(silent=True) or {}
    print(f"[HIT] /send-register-otp -> {body}")

    name = str(body.get("name", "")).strip()
    user_id = str(body.get("userId", "")).strip()
    phone = normalize_phone(body.get("phone", ""))

    if not name:
        return json_response(400, {"success": False, "message": "Name is required."})
    if not user_id:
        return json_response(400, {"success": False, "message": "User ID is required."})
    if not is_valid_phone(phone):
        return json_response(400, {"success": False, "message": "Phone number must be exactly 10 digits."})

    users = read_users()
    normalized_id = normalize_user_id(user_id)

    if any(user.get("userIdNormalized") == normalized_id for user in users):
        return json_response(409, {"success": False, "message": "This user ID is already registered."})
    if any(user.get("phoneNumber") == phone for user in users):
        return json_response(409, {"success": False, "message": "This phone number is already registered."})

    otp_meta = create_otp_record(
        "register",
        {
            "fullName": name,
            "userId": user_id,
            "userIdNormalized": normalized_id,
            "phoneNumber": phone,
        },
    )

    return json_response(
        200,
        {
            "success": True,
            "message": f"Registration OTP sent. Check backend terminal for OTP for {otp_meta['maskedPhoneNumber']}.",
            **otp_meta,
        },
    )


@app.route("/verify-register-otp", methods=["POST"])
def verify_register_otp():
    body = request.get_json(silent=True) or {}
    print(f"[HIT] /verify-register-otp -> {body}")

    record, error = verify_otp_record(body.get("otpRequestId", ""), body.get("otp", ""))
    if error:
        return error

    if record["flow"] != "register":
        return json_response(400, {"success": False, "message": "This OTP request is not for registration."})

    users = read_users()
    payload = record["payload"]

    if any(user.get("userIdNormalized") == payload["userIdNormalized"] for user in users):
        return json_response(409, {"success": False, "message": "This user ID is already registered."})
    if any(user.get("phoneNumber") == payload["phoneNumber"] for user in users):
        return json_response(409, {"success": False, "message": "This phone number is already registered."})

    user = {
        "id": str(uuid.uuid4()),
        "fullName": payload["fullName"],
        "userId": payload["userId"],
        "userIdNormalized": payload["userIdNormalized"],
        "phoneNumber": payload["phoneNumber"],
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    users.append(user)
    write_users(users)

    return json_response(200, {"success": True, "message": "Registration successful.", "user": build_public_user(user)})


@app.route("/send-login-otp", methods=["POST"])
def send_login_otp():
    body = request.get_json(silent=True) or {}
    print(f"[HIT] /send-login-otp -> {body}")

    identifier = str(body.get("identifier") or body.get("phoneNumber") or body.get("userId") or "").strip()
    if not identifier:
        return json_response(400, {"success": False, "message": "Phone number or user ID is required."})

    if identifier.isdigit():
        phone = normalize_phone(identifier)
        if not is_valid_phone(phone):
            return json_response(400, {"success": False, "message": "Phone number must be exactly 10 digits."})

    user = find_user_by_identifier(identifier)
    if not user:
        return json_response(404, {"success": False, "message": "No account found for this phone number or user ID."})

    otp_meta = create_otp_record(
        "login",
        {
            "userRecordId": user["id"],
            "userId": user.get("userId", ""),
            "phoneNumber": user["phoneNumber"],
        },
    )

    return json_response(
        200,
        {
            "success": True,
            "message": f"Login OTP sent. Check backend terminal for OTP for {otp_meta['maskedPhoneNumber']}.",
            **otp_meta,
        },
    )


@app.route("/verify-login-otp", methods=["POST"])
def verify_login_otp():
    body = request.get_json(silent=True) or {}
    print(f"[HIT] /verify-login-otp -> {body}")

    record, error = verify_otp_record(body.get("otpRequestId", ""), body.get("otp", ""))
    if error:
        return error

    if record["flow"] != "login":
        return json_response(400, {"success": False, "message": "This OTP request is not for login."})

    users = read_users()
    user = next((item for item in users if item.get("id") == record["payload"]["userRecordId"]), None)
    if not user:
        return json_response(404, {"success": False, "message": "User not found. Please register again."})

    return json_response(200, {"success": True, "message": "Login successful.", "user": build_public_user(user)})


@app.route("/send-sos", methods=["POST"])
def send_sos():
    body = request.get_json(silent=True) or {}
    print(f"[HIT] /send-sos -> {body}")

    payload, error = validate_sos_payload(body)
    if error:
        return error

    cooldown_key = get_sos_cooldown_key(payload["phone"], body.get("clientId", ""))
    cooldown_remaining = get_sos_cooldown_remaining(cooldown_key)
    if cooldown_remaining:
        return json_response(
            429,
            {
                "success": False,
                "message": f"Please wait {cooldown_remaining} seconds before sending another SOS alert.",
                "cooldownRemaining": cooldown_remaining,
            },
        )

    try:
        message = build_sos_message(payload["lat"], payload["lng"])
        provider, response_text = send_sms(payload["phone"], message)
    except requests.RequestException as exc:
        return json_response(502, {"success": False, "message": f"{SMS_PROVIDER.upper()} request failed: {exc}"})
    except RuntimeError as exc:
        return json_response(500, {"success": False, "message": str(exc)})

    lowered = response_text.lower()
    rejection_markers = ["error", "invalid", "failed", "denied", "unauthor", "reject", "missing"]
    if not response_text:
        return json_response(502, {"success": False, "message": f"{provider.upper()} returned an empty response."})
    if any(marker in lowered for marker in rejection_markers):
        return json_response(502, {"success": False, "message": f"{provider.upper()} rejected SMS: {response_text}"})

    SOS_COOLDOWN_STORE[cooldown_key] = time.time()
    return json_response(
        200,
        {
            "success": True,
            "status": "sent",
            "provider": provider,
            "cooldownSeconds": SOS_COOLDOWN_SECONDS,
            "mapsLink": f"https://maps.google.com/?q={payload['lat']:.6f},{payload['lng']:.6f}",
            "providerResponse": response_text,
        },
    )


@app.route("/", methods=["GET"])
def home():
    return json_response(200, {"success": True, "message": "E-SURAKSHA OTP backend is running."})


if __name__ == "__main__":
    ensure_data_files()
    port = int(os.environ.get("PORT", 5000))
    print(f"E-SURAKSHA OTP backend started successfully on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

