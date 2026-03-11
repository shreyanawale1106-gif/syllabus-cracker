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

    reset_link = f"{APP_URL}/?reset_token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Password Reset - Syllabus Cracker"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    msg.set_content(f"""
Click below to reset your password:

{reset_link}
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

    return ""

# ==========================
# SPLIT TEXT INTO CHUNKS
# ==========================

def split_into_chunks(text, words_per_chunk=600):

    words = text.split()

    chunks = []

    for i in range(0, len(words), words_per_chunk):

        chunk = " ".join(words[i:i+words_per_chunk])

        chunks.append(chunk)

    return chunks

# ==========================
# GENERATE STUDY SCHEDULE
# ==========================

def generate_schedule(subject_chunks, exam_date, hours_per_day):

    today = date.today()

    total_days = (exam_date - today).days + 1

    if total_days <= 0:
        return []

    subjects = list(subject_chunks.keys())

    if len(subjects) == 0:
        return []

    schedule = []

    STUDY_BLOCK = 1.5
    BREAK_TIME = 0.25

    for day_index in range(total_days):

        current_day = today + timedelta(days=day_index)

        day_plan = []

        current_time = 9.0
        studied_hours = 0
        subject_index = 0

        while studied_hours < hours_per_day:

            subject = subjects[subject_index % len(subjects)]

            if not subject_chunks[subject]:
                subject_index += 1
                continue

            chunk = subject_chunks[subject].pop(0)

            end_time = current_time + STUDY_BLOCK

            start_h = int(current_time)
            start_m = int((current_time % 1) * 60)

            end_h = int(end_time)
            end_m = int((end_time % 1) * 60)

            time_slot = f"{start_h:02d}:{start_m:02d} - {end_h:02d}:{end_m:02d}"

            day_plan.append({
                "type": "study",
                "time": time_slot,
                "subject": subject,
                "content": chunk
            })

            studied_hours += STUDY_BLOCK
            current_time = end_time

            if studied_hours >= hours_per_day:
                break

            # break
            break_end = current_time + BREAK_TIME

            b_start_h = int(current_time)
            b_start_m = int((current_time % 1) * 60)

            b_end_h = int(break_end)
            b_end_m = int((break_end % 1) * 60)

            break_slot = f"{b_start_h:02d}:{b_start_m:02d} - {b_end_h:02d}:{b_end_m:02d}"

            day_plan.append({
                "type": "break",
                "time": break_slot
            })

            current_time = break_end

            # lunch break
            if 12 <= current_time <= 13:

                lunch_end = current_time + 1

                l_start_h = int(current_time)
                l_end_h = int(lunch_end)

                day_plan.append({
                    "type": "lunch",
                    "time": f"{l_start_h:02d}:00 - {l_end_h:02d}:00"
                })

                current_time = lunch_end

            subject_index += 1

        if not day_plan:
            break

        schedule.append({
            "date": current_day.isoformat(),
            "tasks": day_plan
        })

        finished = True
        for s in subjects:
            if subject_chunks[s]:
                finished = False
                break

        if finished:
            break

    return schedule

# ==========================
# MAIN APP
# ==========================

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
        hours_per_day = st.slider("Study hours per day", 1.0, 10.0, 4.0, 0.5)

    if st.button("Generate Study Plan"):

        if not uploaded_files:
            st.warning("Upload syllabus files")
            return

        subject_chunks = {}

        for file in uploaded_files:

            subject = file.name.split(".")[0]

            text = extract_text_from_upload(file)

            if not text.strip():
                st.warning(f"No text extracted from {subject}")
                continue

            chunks = split_into_chunks(text)

            subject_chunks[subject] = chunks

        schedule = generate_schedule(
            subject_chunks,
            exam_date,
            hours_per_day
        )

        if not schedule:
            st.error("Could not generate schedule")
            return

        st.subheader("📅 Study Plan")

        for day in schedule:

            st.markdown(f"# 📅 {day['date']}")

            for task in day["tasks"]:

                if task["type"] == "study":

                    st.markdown(
                        f"### 📖 {task['time']} — **{task['subject']}**"
                    )

                    with st.expander("Topics / Content"):

                        sentences = task["content"].split(". ")

                        for s in sentences[:8]:
                            st.write("•", s.strip())

                elif task["type"] == "break":

                    st.markdown(f"☕ **Break:** {task['time']}")

                elif task["type"] == "lunch":

                    st.markdown(f"🍽 **Lunch Break:** {task['time']}")

            st.markdown("---")

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

# ==========================
# RUN APP
# ==========================

if __name__ == "__main__":
    auth_system()
