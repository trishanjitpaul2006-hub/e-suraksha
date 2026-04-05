const BASE_URL = "https://e-suraksha.onrender.com";

// Send OTP
async function sendOTP() {
    const phone = document.getElementById("phone").value;

    if (phone.length !== 10) {
        alert("Enter valid 10-digit phone number");
        return;
    }

    const res = await fetch(`${BASE_URL}/send-otp`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ phone })
    });

    const data = await res.json();
    alert(data.message);
}

// Verify OTP
async function verifyOTP() {
    const phone = document.getElementById("phone").value;
    const otp = document.getElementById("otp").value;

    const res = await fetch(`${BASE_URL}/verify-otp`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ phone, otp })
    });

    const data = await res.json();

    if (data.success) {
        alert("Login Successful ✅");
    } else {
        alert("Invalid OTP ❌");
    }
}
