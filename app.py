import streamlit as st
import pdfplumber
import io
import json
import hashlib
import secrets
import smtplib
from email.message import EmailMessage
from datetime import date, timedelta

# ==========================
# CONFIG
# ==========================

USER_FILE = "users.json"
APP_URL = "https://syllabus-cracker-nywxanr28dajtfkpffsjyf.streamlit.app"

SENDER_EMAIL = st.secrets.get("SENDER_EMAIL")
SENDER_PASSWORD = st.secrets.get("SENDER_PASSWORD")

# ==========================
# USER MANAGEMENT
# ==========================

def load_users():
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def delete_user_account(email):
    users = load_users()
    if email in users:
        del users[email]
        save_users(users)

# ==========================
# EMAIL RESET
# ==========================

def send_reset_email(to_email, token):

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        st.error("Email secrets not configured.")
        st.stop()

    reset_link = f"{APP_URL}/?reset_token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Password Reset - Syllabus Cracker"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    msg.set_content(f"""
Click the link below to reset your password:

{reset_link}
""")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        st.error(f"Email sending failed: {str(e)}")
        st.stop()

# ==========================
# TEXT EXTRACTION
# ==========================

def extract_text_from_upload(uploaded_file):

    filename = uploaded_file.name.lower()
    data = uploaded_file.read()

    if filename.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    if filename.endswith(".pdf"):

        text = ""

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"

        return text

    raise ValueError("Unsupported file type.")

# ==========================
# TOPIC EXTRACTION
# ==========================

def split_into_topics(text):

    import re

    topics = []

    # split by lines
    lines = text.split("\n")

    for line in lines:

        clean = line.strip()

        if len(clean) < 5:
            continue

        # split further by comma / semicolon
        parts = re.split(r",|;", clean)

        for part in parts:

            topic = part.strip()

            if len(topic) > 5:
                topics.append(topic)

    return topics

# ==========================
# MULTI SUBJECT SCHEDULER
# ==========================

def generate_schedule_multiple_subjects(subjects_text, exam_date, hours_per_day):

    today = date.today()
    total_days = (exam_date - today).days + 1

    if total_days <= 0:
        return []

    subject_topics = {}

    for subject, text in subjects_text.items():
        subject_topics[subject] = split_into_topics(text)

    subjects = list(subject_topics.keys())

    hours_per_subject = round(hours_per_day / len(subjects), 2)

    plan = []

    day_index = 0

    while True:

        if day_index >= total_days:
            break

        current_day = today + timedelta(days=day_index)

        finished = 0

        for subject in subjects:

            if not subject_topics[subject]:
                finished += 1
                continue

            topic = subject_topics[subject].pop(0)

            plan.append({
                "date": current_day.isoformat(),
                "subject": subject,
                "topic": topic,
                "hours": hours_per_subject
            })

        if finished == len(subjects):
            break

        day_index += 1

    return plan

# ==========================
# MAIN APP
# ==========================

def main_app():

    email = st.session_state["user"]

    with st.sidebar:

        st.write(f"Logged in as: **{email}**")

        if st.button("Log out"):
            st.session_state.logged_in = False
            st.rerun()

        st.markdown("---")

        if st.button("🗑️ Delete Account"):
            st.session_state.confirm_delete = True

        if st.session_state.get("confirm_delete"):

            st.warning("This action cannot be undone.")

            col1, col2 = st.columns(2)

            with col1:

                if st.button("Yes, Delete My Account"):

                    delete_user_account(email)
                    st.session_state.logged_in = False
                    st.success("Account deleted.")
                    st.rerun()

            with col2:

                if st.button("Cancel"):
                    st.session_state.confirm_delete = False
                    st.rerun()

    st.title("📚 Syllabus Cracker")

    uploaded_files = st.file_uploader(
        "Upload Syllabus Files (Multiple Subjects)",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )

    col1, col2 = st.columns(2)

    with col1:
        exam_date = st.date_input("Exam Date", min_value=date.today())

    with col2:
        hours_per_day = st.slider("Study hours per day", 1.0, 10.0, 3.0, 0.5)

    if st.button("Generate Study Plan"):

        if not uploaded_files:
            st.warning("Upload at least one syllabus file.")
            return

        subjects_text = {}

        for file in uploaded_files:

            subject_name = file.name.split(".")[0]

            text = extract_text_from_upload(file)

            if text.strip():
                subjects_text[subject_name] = text

        schedule = generate_schedule_multiple_subjects(
            subjects_text,
            exam_date,
            hours_per_day
        )

        if not schedule:
            st.error("Not enough time before exam.")
            return

        st.subheader("📅 Study Plan")

        current_date = ""

        for item in schedule:

            if current_date != item["date"]:
                current_date = item["date"]
                st.markdown(f"## 📅 {current_date}")

            st.markdown(
                f"**{item['subject']}** — {item['topic']} — ⏱ {item['hours']} hrs"
            )

# ==========================
# AUTH SYSTEM
# ==========================

def auth_system():

    users = load_users()

    token = st.query_params.get("reset_token")

    if token:

        for email, data in users.items():

            if data.get("reset_token") == token:

                st.title("Reset Password")

                new_password = st.text_input("New Password", type="password")

                if st.button("Update Password"):

                    users[email]["password"] = hash_password(new_password)
                    users[email].pop("reset_token", None)

                    save_users(users)

                    st.success("Password updated. Please login.")
                    st.stop()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        main_app()
        return

    st.title("🔐 Login")

    menu = st.radio("", ["Login", "Register", "Forgot Password"])

    if menu == "Login":

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login"):

            if email in users and users[email]["password"] == hash_password(password):

                st.session_state.logged_in = True
                st.session_state.user = email
                st.rerun()

            else:
                st.error("Invalid credentials")

    elif menu == "Register":

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Create Account"):

            if email in users:
                st.error("User already exists")

            else:
                users[email] = {"password": hash_password(password)}
                save_users(users)
                st.success("Account created. Please login.")

    elif menu == "Forgot Password":

        email = st.text_input("Enter your registered email")

        if st.button("Send Reset Link"):

            if email in users:

                token = secrets.token_urlsafe(16)
                users[email]["reset_token"] = token

                save_users(users)

                send_reset_email(email, token)

                st.success("Reset link sent to your email.")

            else:
                st.error("Email not found")

# ==========================

if __name__ == "__main__":
    auth_system()
