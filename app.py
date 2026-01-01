import streamlit as st
import pdfplumber
import io
from datetime import date, datetime, timedelta


# ---------- 1. TEXT EXTRACTION ---------- #

def extract_text_from_upload(uploaded_file) -> str:
    """
    Extract text from an uploaded PDF or TXT file.
    """
    if uploaded_file is None:
        return ""

    filename = uploaded_file.name.lower()
    data = uploaded_file.read()

    # TXT
    if filename.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    # PDF
    if filename.endswith(".pdf"):
        text = ""
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
        return text

    raise ValueError("Unsupported file type. Please upload a .pdf or .txt file.")


# ---------- 2. PARSE SYLLABUS INTO UNITS & TOPICS ---------- #

def parse_syllabus(raw_text):
    """
    Simple heuristic parser:
    - Lines starting with 'Unit' or 'Module' become unit titles
    - Bullet lines (-, *, •, ▪) become topics
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    units = []
    current_unit = None

    for line in lines:
        lower = line.lower()

        # New unit/module
        if lower.startswith("unit") or lower.startswith("module"):
            if current_unit:
                units.append(current_unit)
            current_unit = {"unit_title": line, "topics": []}

        # Bullet point -> topic
        elif line.startswith(("-", "*", "•", "▪")):
            if current_unit is None:
                current_unit = {"unit_title": "General", "topics": []}
            topic_text = line[1:].strip()
            current_unit["topics"].append({
                "topic": topic_text,
                "difficulty": "medium"
            })

        # Normal line → continuation or standalone topic
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


# ---------- 3. STUDY PLAN GENERATION ---------- #

def estimate_hours(difficulty: str) -> float:
    """
    Map difficulty to estimated hours.
    """
    difficulty = difficulty.lower()
    if difficulty == "easy":
        return 1.0
    if difficulty == "hard":
        return 3.0
    return 2.0


def generate_schedule(units, exam_date, hours_per_day):
    """
    Assign topics day by day from today until exam date.
    """
    today = date.today()
    current_day = today
    remaining_hours_today = hours_per_day
    plan = []

    for unit in units:
        for topic in unit["topics"]:
            hours_needed = estimate_hours(topic.get("difficulty", "medium"))

            while hours_needed > 0 and current_day <= exam_date:
                if remaining_hours_today <= 0:
                    current_day += timedelta(days=1)
                    remaining_hours_today = hours_per_day
                    continue

                allocated = min(hours_needed, remaining_hours_today)

                plan.append({
                    "date": current_day.isoformat(),
                    "unit_title": unit["unit_title"],
                    "topic": topic["topic"],
                    "allocated_hours": round(allocated, 2),
                })

                hours_needed -= allocated
                remaining_hours_today -= allocated

            if current_day > exam_date:
                break

        if current_day > exam_date:
            break

    return plan


# ---------- 4. SIMPLE UNIT SUMMARY ---------- #

def summarize_unit(unit):
    topics = [t["topic"] for t in unit["topics"]]
    if not topics:
        return f"This unit covers topics related to {unit['unit_title']}."
    joined = "; ".join(topics[:4])
    return f"This unit ({unit['unit_title']}) includes: {joined}."


# ---------- 5. STREAMLIT APP UI ---------- #

def main():
    # Sidebar logout button
    with st.sidebar:
        st.write(f"Logged in as: **admin**")
        if st.button("Log out"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("📚 Syllabus Cracker")
    st.caption("Upload your syllabus and generate a personalized study plan.")

    uploaded_file = st.file_uploader(
        "Upload Syllabus (.pdf or .txt)",
        type=["pdf", "txt"]
    )

    col1, col2 = st.columns(2)
    with col1:
        exam_date = st.date_input("📅 Exam Date", min_value=date.today())
    with col2:
        hours_per_day = st.slider(
            "⏱️ Study hours per day",
            1.0, 10.0, 2.0, 0.5
        )

    if st.button("✨ Generate Study Plan"):
        if uploaded_file is None:
            st.warning("Please upload a syllabus file first.")
            return

        try:
            raw_text = extract_text_from_upload(uploaded_file)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            return

        if not raw_text.strip():
            st.error("Could not extract any text from the file.")
            return

        units = parse_syllabus(raw_text)

        if not units:
            st.error("Could not detect any units or topics.")
            return

        for unit in units:
            unit["summary"] = summarize_unit(unit)

        schedule = generate_schedule(units, exam_date, hours_per_day)

        st.success("Study plan generated successfully!")

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("📚 Units & Summaries")
            for i, unit in enumerate(units, start=1):
                with st.expander(f"Unit {i}: {unit['unit_title']}", expanded=(i == 1)):
                    st.markdown(f"**Summary:** {unit['summary']}")
                    st.markdown("**Topics:**")
                    for j, t in enumerate(unit["topics"], start=1):
                        st.markdown(f"- {j}. {t['topic']}")

        with col_right:
            st.subheader("🗓️ Study Plan")
            if not schedule:
                st.warning("Not enough days to schedule all topics.")
            else:
                for item in schedule:
                    st.markdown(
                        f"**{item['date']}** → *{item['unit_title']}* – "
                        f"{item['topic']} (`{item['allocated_hours']} hrs`)"
                    )

# ---------- 6. LOGIN LOGIC ---------- #

def login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        # Centered layout for login screen
        st.set_page_config(page_title="Syllabus Cracker - Login", layout="centered")
        
        st.markdown("<h1 style='text-align: center;'>🔐 Admin Login</h1>", unsafe_allow_html=True)
        
        # Create a container for the login form
        with st.container():
            user = st.text_input("Username", placeholder="Enter admin")
            password = st.text_input("Password", type="password", placeholder="Enter admin")
            
            if st.button("Login", use_container_width=True):
                if user == "admin" and password == "admin":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
    else:
        # Wide layout for the main application
        st.set_page_config(page_title="Syllabus Cracker", layout="wide")
        main()

if __name__ == "__main__":
    login()
