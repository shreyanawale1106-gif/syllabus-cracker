import streamlit as st
import pdfplumber
import io
from datetime import date, datetime, timedelta


# ---------------- LOGIN PAGE ---------------- #

def login_page():
    st.set_page_config(page_title="Login - Syllabus Cracker", layout="centered")
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin":
            st.session_state["logged_in"] = True
            st.success("Login successful!")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")


# ---------- 1. TEXT EXTRACTION ---------- #

def extract_text_from_upload(uploaded_file) -> str:
    if uploaded_file is None:
        return ""

    filename = uploaded_file.name.lower()
    data = uploaded_file.read()

    if filename.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    if filename.endswith(".pdf"):
        text = ""
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
        return text

    raise ValueError("Unsupported file type.")


# ---------- 2. PARSE SYLLABUS ---------- #

def parse_syllabus(raw_text):
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    units = []
    current_unit = None

    for line in lines:
        lower = line.lower()

        if lower.startswith("unit") or lower.startswith("module"):
            if current_unit:
                units.append(current_unit)
            current_unit = {"unit_title": line, "topics": []}

        elif line.startswith(("-", "*", "•", "▪")):
            if current_unit is None:
                current_unit = {"unit_title": "General", "topics": []}
            current_unit["topics"].append({
                "topic": line[1:].strip(),
                "difficulty": "medium"
            })
        else:
            if current_unit is None:
                current_unit = {"unit_title": "General", "topics": []}
            if current_unit["topics"]:
                current_unit["topics"][-1]["topic"] += " " + line
            else:
                current_unit["topics"].append({
                    "topic": line,
                    "difficulty": "medium"
                })

    if current_unit:
        units.append(current_unit)

    return units


# ---------- 3. STUDY PLAN ---------- #

def estimate_hours(difficulty):
    if difficulty == "easy":
        return 1
    if difficulty == "hard":
        return 3
    return 2


def generate_schedule(units, exam_date, hours_per_day):
    today = date.today()
    current_day = today
    remaining = hours_per_day
    plan = []

    for unit in units:
        for topic in unit["topics"]:
            hours_needed = estimate_hours(topic["difficulty"])

            while hours_needed > 0 and current_day <= exam_date:
                if remaining <= 0:
                    current_day += timedelta(days=1)
                    remaining = hours_per_day
                    continue

                plan.append({
                    "date": current_day,
                    "unit": unit["unit_title"],
                    "topic": topic["topic"]
                })

                hours_needed -= 1
                remaining -= 1

    return plan


# ---------- MAIN APP ---------- #

def main():
    st.set_page_config(page_title="Syllabus Cracker", layout="wide")
    st.title("📚 Syllabus Cracker")

    uploaded_file = st.file_uploader("Upload syllabus (PDF/TXT)", type=["pdf", "txt"])

    col1, col2 = st.columns(2)
    with col1:
        exam_date = st.date_input("Exam Date", min_value=date.today())
    with col2:
        hours = st.slider("Study hours per day", 1, 10, 2)

    if st.button("Generate Study Plan"):
        text = extract_text_from_upload(uploaded_file)
        units = parse_syllabus(text)
        schedule = generate_schedule(units, exam_date, hours)

        for item in schedule:
            st.write(f"{item['date']} → {item['topic']}")


# ---------- APP ENTRY POINT ---------- #

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.session_state["logged_in"]:
    main()
else:
    login_page()
