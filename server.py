import json
import os
import random
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
OTP_EXPIRY_SECONDS = 300
OTP_STORE = {}


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


@app.route("/", methods=["GET"])
def home():
    return json_response(200, {"success": True, "message": "E-SURAKSHA OTP backend is running."})


if __name__ == "__main__":
    ensure_data_files()
    port = int(os.environ.get("PORT", 5000))
    print(f"E-SURAKSHA OTP backend started successfully on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

