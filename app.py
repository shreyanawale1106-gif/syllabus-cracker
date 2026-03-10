import streamlit as st
import pdfplumber
import io
import json
import hashlib
import secrets
import smtplib
import re
from email.message import EmailMessage
from datetime import date, timedelta

USER_FILE = "users.json"
APP_URL = "https://syllabus-cracker-nywxanr28dajtfkpffsjyf.streamlit.app"

SENDER_EMAIL = st.secrets.get("SENDER_EMAIL")
SENDER_PASSWORD = st.secrets.get("SENDER_PASSWORD")


# ---------------------------
# USER MANAGEMENT
# ---------------------------

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


# ---------------------------
# EMAIL RESET
# ---------------------------

def send_reset_email(to_email, token):

    reset_link = f"{APP_URL}/?reset_token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Password Reset - Syllabus Cracker"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    msg.set_content(f"""
Reset your password:

{reset_link}
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)


# ---------------------------
# TEXT EXTRACTION
# ---------------------------

def extract_text_from_upload(uploaded_file):

    filename = uploaded_file.name.lower()
    data = uploaded_file.read()

    if filename.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    if filename.endswith(".pdf"):

        text = ""

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"

        return text

    return ""


# ---------------------------
# TOPIC EXTRACTION (FIXED)
# ---------------------------

def extract_topics(text):

    topics = []

    lines = text.split("\n")

    for line in lines:

        clean = line.strip()

        if len(clean) < 6:
            continue

        # remove numbering
        clean = re.sub(r"^[0-9]+[\.\)]", "", clean)

        # split by comma / semicolon
        parts = re.split(r",|;|:", clean)

        for part in parts:

            topic = part.strip()

            if len(topic) > 6:
                topics.append(topic)

    return topics


# ---------------------------
# SCHEDULE GENERATOR
# ---------------------------

def generate_schedule(subject_topics, exam_date, hours_per_day):

    today = date.today()
    total_days = (exam_date - today).days + 1

    if total_days <= 0:
        return []

    all_topics = []

    for subject, topics in subject_topics.items():
        for t in topics:
            all_topics.append((subject, t))

    if not all_topics:
        return []

    topics_per_day = max(1, len(all_topics) // total_days)

    hours_per_topic = round(hours_per_day / topics_per_day, 2)

    schedule = []
    topic_index = 0

    for day in range(total_days):

        day_date = today + timedelta(days=day)

        daily = all_topics[topic_index:topic_index+topics_per_day]

        if not daily:
            break

        entries = []

        for subject, topic in daily:
            entries.append({
                "subject": subject,
                "topic": topic,
                "hours": hours_per_topic
            })

        schedule.append({
            "date": day_date.isoformat(),
            "topics": entries
        })

        topic_index += topics_per_day

    return schedule


# ---------------------------
# MAIN APP
# ---------------------------

def main_app():

    email = st.session_state["user"]

    with st.sidebar:

        st.write(f"Logged in as **{email}**")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

        st.markdown("---")

        if st.button("Delete Account"):
            delete_user_account(email)
            st.session_state.logged_in = False
            st.success("Account deleted")
            st.rerun()

    st.title("📚 Syllabus Cracker")

    uploaded_files = st.file_uploader(
        "Upload syllabus files",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )

    col1, col2 = st.columns(2)

    with col1:
        exam_date = st.date_input("Exam Date", min_value=date.today())

    with col2:
        hours_per_day = st.slider("Hours per day", 1.0, 10.0, 4.0, 0.5)

    if st.button("Generate Study Plan"):

        if not uploaded_files:
            st.warning("Upload syllabus files")
            return

        subject_topics = {}

        for file in uploaded_files:

            subject = file.name.split(".")[0]

            text = extract_text_from_upload(file)

            topics = extract_topics(text)

            subject_topics[subject] = topics

        schedule = generate_schedule(
            subject_topics,
            exam_date,
            hours_per_day
        )

        if not schedule:
            st.error("Could not generate schedule")
            return

        st.subheader("📅 Study Plan")

        for day in schedule:

            st.markdown(f"## 📅 {day['date']}")

            for t in day["topics"]:

                st.write(
                    f"📘 **{t['subject']}** — {t['topic']} "
                    f"⏱ {t['hours']} hrs"
                )

            st.markdown("---")


# ---------------------------
# AUTH
# ---------------------------

def auth_system():

    users = load_users()

    token = st.query_params.get("reset_token")

    if token:

        for email, data in users.items():

            if data.get("reset_token") == token:

                st.title("Reset Password")

                new_password = st.text_input(
                    "New Password",
                    type="password"
                )

                if st.button("Update Password"):

                    users[email]["password"] = hash_password(new_password)
                    users[email].pop("reset_token", None)

                    save_users(users)

                    st.success("Password updated")
                    st.stop()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        main_app()
        return

    st.title("Login")

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
                st.error("User exists")
            else:

                users[email] = {
                    "password": hash_password(password)
                }

                save_users(users)

                st.success("Account created")

    elif menu == "Forgot Password":

        email = st.text_input("Enter email")

        if st.button("Send Reset Link"):

            if email in users:

                token = secrets.token_urlsafe(16)

                users[email]["reset_token"] = token

                save_users(users)

                send_reset_email(email, token)

                st.success("Reset email sent")

            else:
                st.error("Email not found")


if __name__ == "__main__":
    auth_system()
