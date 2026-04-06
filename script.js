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

