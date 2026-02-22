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
# SEND RESET EMAIL
# ==========================

def send_reset_email(to_email, token):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        st.error("Email secrets not configured properly.")
        st.stop()

    reset_link = f"{APP_URL}/?reset_token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Password Reset - Syllabus Cracker"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg.set_content(f"""
Click the link below to reset your password:

{reset_link}

If you did not request this, ignore this email.
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

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
# CHUNK TEXT INTO STUDY BLOCKS
# ==========================

def split_into_chunks(text, words_per_chunk=800):
    words = text.split()
    chunks = []

    for i in range(0, len(words), words_per_chunk):
        chunk_words = words[i:i+words_per_chunk]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)

    return chunks

# ==========================
# GENERATE SCHEDULE
# ==========================

def generate_schedule_from_text(raw_text, exam_date, hours_per_day):
    today = date.today()
    total_days = (exam_date - today).days + 1

    if total_days <= 0:
        return []

    chunks = split_into_chunks(raw_text)

    if not chunks:
        return []

    chunks_per_day = max(1, len(chunks) // total_days)

    plan = []
    chunk_index = 0

    for day_offset in range(total_days):
        current_day = today + timedelta(days=day_offset)
        daily_chunks = chunks[chunk_index:chunk_index+chunks_per_day]

        if not daily_chunks:
            break

        combined_text = "\n\n".join(daily_chunks)

        plan.append({
            "date": current_day.isoformat(),
            "title": f"Study Sections {chunk_index+1} - {chunk_index+len(daily_chunks)}",
            "content": combined_text,
            "hours": hours_per_day
        })

        chunk_index += chunks_per_day

        if chunk_index >= len(chunks):
            break

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
            delete_user_account(email)
            st.session_state.logged_in = False
            st.success("Account deleted.")
            st.rerun()

    st.title("📚 Syllabus Cracker")

    uploaded_file = st.file_uploader(
        "Upload Syllabus (.pdf or .txt)",
        type=["pdf", "txt"]
    )

    col1, col2 = st.columns(2)
    with col1:
        exam_date = st.date_input("Exam Date", min_value=date.today())
    with col2:
        hours_per_day = st.slider("Study hours per day", 1.0, 10.0, 2.0, 0.5)

    if st.button("Generate Study Plan"):

        if uploaded_file is None:
            st.warning("Upload a syllabus file.")
            return

        raw_text = extract_text_from_upload(uploaded_file)

        if not raw_text.strip():
            st.error("No text extracted from file.")
            return

        schedule = generate_schedule_from_text(
            raw_text,
            exam_date,
            hours_per_day
        )

        if not schedule:
            st.error("Not enough time before exam or empty file.")
            return

        st.subheader("📅 Study Plan")

        for item in schedule:
            st.markdown(f"## 📅 {item['date']}")
            st.markdown(f"**{item['title']}** — {item['hours']} hrs")

            # Expandable content preview
            with st.expander("📖 View Topics Covered"):
                preview_lines = item["content"].split(". ")
                for line in preview_lines[:8]:  # show first 8 points
                    st.write("•", line.strip())

            st.markdown("---")

# ==========================
# AUTH SYSTEM
# ==========================

def auth_system():
    users = load_users()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        main_app()
        return

    st.title("🔐 Login")

    menu = st.radio("", ["Login", "Register"])

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

if __name__ == "__main__":
    auth_system()
