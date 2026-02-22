import streamlit as st
import json
import hashlib
import uuid
import os
import smtplib
from email.mime.text import MIMEText

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Syllabus Cracker", layout="centered")

USERS_FILE = "users.json"

# ---------------- FILE HANDLING ----------------
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ---------------- PASSWORD ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- EMAIL ----------------
def send_reset_email(receiver_email, token):
    try:
        sender_email = st.secrets["SENDER_EMAIL"]
        sender_password = st.secrets["SENDER_PASSWORD"]
    except Exception:
        st.error("Email secrets not configured.")
        return

    reset_link = f"{st.secrets.get('APP_URL', '')}?reset_token={token}"

    msg = MIMEText(f"Click to reset your password:\n\n{reset_link}")
    msg["Subject"] = "Password Reset - Syllabus Cracker"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        st.success("Reset link sent to your email.")
    except Exception as e:
        st.error("Failed to send email.")
        st.exception(e)

# ---------------- AUTH SYSTEM ----------------
def auth_system():
    users = load_users()

    # FIXED RADIO LABEL
    menu = st.radio(
        "Select Option",
        ["Login", "Register", "Forgot Password"],
        label_visibility="collapsed"
    )

    # ---------------- LOGIN ----------------
    if menu == "Login":
        st.subheader("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if email in users and users[email]["password"] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.user = email
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    # ---------------- REGISTER ----------------
    elif menu == "Register":
        st.subheader("Register")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Register"):
            if email in users:
                st.error("User already exists")
            else:
                users[email] = {
                    "password": hash_password(password),
                    "reset_token": None
                }
                save_users(users)
                st.success("Registration successful!")

    # ---------------- FORGOT PASSWORD ----------------
    elif menu == "Forgot Password":
        st.subheader("Forgot Password")
        email = st.text_input("Enter your registered email")

        if st.button("Send Reset Link"):
            if email in users:
                token = str(uuid.uuid4())
                users[email]["reset_token"] = token
                save_users(users)
                send_reset_email(email, token)
            else:
                st.error("Email not found")

# ---------------- RESET PASSWORD PAGE ----------------
def reset_password_page(token):
    users = load_users()
    for email, data in users.items():
        if data.get("reset_token") == token:
            st.subheader("Reset Password")
            new_password = st.text_input("New Password", type="password")

            if st.button("Update Password"):
                users[email]["password"] = hash_password(new_password)
                users[email]["reset_token"] = None
                save_users(users)
                st.success("Password updated successfully!")
                st.info("You can now login.")
                return
    st.error("Invalid or expired token.")

# ---------------- MAIN ----------------
def main():
    query_params = st.query_params

    if "reset_token" in query_params:
        reset_password_page(query_params["reset_token"])
        return

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        st.title("Welcome to Syllabus Cracker 🎓")
        st.write(f"Logged in as: {st.session_state.user}")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
    else:
        auth_system()

if __name__ == "__main__":
    main()
