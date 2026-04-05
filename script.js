const BASE_URL = "https://e-suraksha.onrender.com";

// Send Register OTP
async function sendRegisterOTP() {
    const name = document.getElementById("name").value;
    const userId = document.getElementById("userId").value;
    const phone = document.getElementById("phone").value;

    const res = await fetch(`${BASE_URL}/send-register-otp`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, userId, phone })
    });

    const data = await res.json();
    alert(data.message);

    window.otpRequestId = data.otpRequestId;
}

// Verify Register OTP
async function verifyRegisterOTP() {
    const otp = document.getElementById("otp").value;

    const res = await fetch(`${BASE_URL}/verify-register-otp`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            otpRequestId: window.otpRequestId,
            otp: otp
        })
    });

    const data = await res.json();
    alert(data.message);
}

// Send Login OTP
async function sendLoginOTP() {
    const identifier = document.getElementById("loginId").value;

    const res = await fetch(`${BASE_URL}/send-login-otp`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ identifier })
    });

    const data = await res.json();
    alert(data.message);

    window.loginOtpId = data.otpRequestId;
}

// Verify Login OTP
async function verifyLoginOTP() {
    const otp = document.getElementById("loginOtp").value;

    const res = await fetch(`${BASE_URL}/verify-login-otp`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            otpRequestId: window.loginOtpId,
            otp: otp
        })
    });

    const data = await res.json();
    alert(data.message);
}
