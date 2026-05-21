// Initialize localStorage "users" if not exist
if (!localStorage.getItem("users")) {
    localStorage.setItem("users", JSON.stringify({}));
}

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const loginContainer = document.getElementById("loginFormContainer");
const registerContainer = document.getElementById("registerFormContainer");

const showRegister = document.getElementById("showRegister");
const showLogin = document.getElementById("showLogin");

// Toggle forms
showRegister.addEventListener("click", e => {
    e.preventDefault();
    loginContainer.style.display = "none";
    registerContainer.style.display = "block";
});

showLogin.addEventListener("click", e => {
    e.preventDefault();
    registerContainer.style.display = "none";
    loginContainer.style.display = "block";
});

// Login
loginForm.addEventListener("submit", e => {
    e.preventDefault();
    const username = document.getElementById("loginUsername").value;
    const password = document.getElementById("loginPassword").value;

    let users = JSON.parse(localStorage.getItem("users"));
    if (users[username] && users[username] === password) {
        alert("Login Successful!");
        loginForm.reset();
    } else {
        alert("Invalid username or password!");
    }
});

// Register
registerForm.addEventListener("submit", e => {
    e.preventDefault();
    const username = document.getElementById("registerUsername").value;
    const password = document.getElementById("registerPassword").value;

    let users = JSON.parse(localStorage.getItem("users"));
    if (users[username]) {
        alert("Username already exists!");
    } else {
        users[username] = password;
        localStorage.setItem("users", JSON.stringify(users));
        alert("Registration Successful! You can now login.");
        registerForm.reset();
        // Switch to login form
        registerContainer.style.display = "none";
        loginContainer.style.display = "block";
    }
});

function normalizeSosPhoneForMsg91(value) {
    const digits = String(value || "").replace(/\D/g, "");
    if (digits.length === 10) return `91${digits}`;
    if (digits.length === 12 && digits.startsWith("91")) return digits;
    return digits;
}

function showSosStatus(message, type = "info") {
    const feedback = document.getElementById("sos-feedback");
    if (!feedback) {
        alert(message);
        return;
    }
    feedback.textContent = message;
    feedback.classList.remove("is-hidden", "is-success", "is-error", "is-info");
    feedback.classList.add(type === "success" ? "is-success" : type === "error" ? "is-error" : "is-info");
}

function getAlternateEmergencyPhone() {
    try {
        const currentUser = JSON.parse(localStorage.getItem("currentUser") || "null");
        const candidate = currentUser?.alternateEmergencyNumber || currentUser?.altPhone || currentUser?.emergencyPhone || "";
        return normalizeSosPhoneForMsg91(candidate);
    } catch (error) {
        return "";
    }
}

function getCurrentPositionAsync() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error("Geolocation is not supported in this browser."));
            return;
        }
        navigator.geolocation.getCurrentPosition(resolve, reject, {
            enableHighAccuracy: true,
            maximumAge: 0,
            timeout: 10000
        });
    });
}

function getGeolocationErrorMessage(error) {
    if (error && error.code === 1) return "Geolocation denied. Allow location access and try again.";
    if (error && error.code === 2) return "Location unavailable. Move to an open area and try again.";
    if (error && error.code === 3) return "Location request timed out. Try again.";
    return "Location access is required to send SOS.";
}

function getSosPhoneErrorMessage(phone) {
    if (!phone) return "No alternate emergency number saved.";
    return "Alternate emergency number is invalid. Use +91XXXXXXXXXX or XXXXXXXXXX.";
}

function getBackendSosErrorMessage(error, payload = {}) {
    if (error instanceof TypeError) return "Backend not reachable. Start server.py on port 5000.";
    const backendMessage = payload.message || error?.message || "SOS sending failed.";
    if (backendMessage.includes("91XXXXXXXXXX")) return "Phone format invalid. Use +91XXXXXXXXXX or XXXXXXXXXX.";
    if (backendMessage.startsWith("MSG91 rejected SMS:")) return backendMessage;
    return backendMessage;
}

async function sendSOS() {
    let position;
    try {
        position = await getCurrentPositionAsync();
    } catch (error) {
        showSosStatus(getGeolocationErrorMessage(error), "error");
        return;
    }

    const lat = position?.coords?.latitude;
    const lng = position?.coords?.longitude;
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        showSosStatus("Valid location is required to send SOS.", "error");
        return;
    }

    const message = `I need help. My location is: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    console.log("[SOS demo]", message);
    showSosStatus(`Emergency alert sent with current location. ${message}`, "success");
    return { ok: true, demo: true, lat, lng, message };
}

window.sendSOS = sendSOS;
