import streamlit as st
import requests
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
from app import faculty_subjects

API_URL = "http://127.0.0.1:5000"

# faculty_subjects = {
#     "Kavita Patil": "DAA",
#     "Kirti Deshpande": "DBMS",
#     "Neeraj Sathawane": "DAV",
#     "Suhasini Bhat": "BCVS",
#     "Raj": "CT",
#     "Kavita Moholkar": "IPR"
# }

def login():
    st.set_page_config(page_title="Attender", page_icon="📊")
    st.title("Attender ERP Portal")
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        response = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
        
        if response.status_code == 200:
            user = response.json()
            st.session_state["username"] = user["username"]
            st.session_state["role"] = user["role"]
            st.session_state["name"] = user["name"]
            st.rerun()
        else:
            st.error("Invalid Credentials")


def faculty_dashboard():
    st.set_page_config(page_title="ERP", page_icon="📊")
    st.title("Faculty Dashboard")
    faculty = st.session_state["name"]
    subject = faculty_subjects.get(faculty, None)

    if subject is None:
        st.error("Unauthorized Faculty")
        return

    col1, col2 = st.columns(2)

    # Display badges side by side
    col1.badge(f"Faculty Name: {faculty}")
    col2.badge(f"Subject Name: {subject}")
    
    st.divider()

    # Fetch student list from API
    response = requests.get(f"{API_URL}/get_students")
    if response.status_code == 200:
        student_list = response.json()
    else:
        st.error("❌ Failed to fetch student list!")
        student_list = []
    unique_student_list = list(set(student_list))
    student = st.selectbox("Select Student", unique_student_list)
    date = st.date_input("Date")
    status = st.selectbox("Attendance", ["Present", "Absent"])

    if st.button("Mark Attendance"):
        response = requests.post(f"{API_URL}/mark_attendance", json={
            "faculty": st.session_state["username"],
            "student": student,
            "date": str(date),
            "status": status
        })

        if response.status_code == 200:
            st.success("✅ Attendance marked successfully!")
        else:
            st.error("❌ Failed to mark attendance.")

    
    if st.button("❌ Delete Selected Attendance"):
        response = requests.post(f"{API_URL}/delete_attendance", json={
            "student": student,
            "date": str(date)
        })

        if response.status_code == 200:
            st.success("✅ Attendance deleted successfully!")
        else:
            st.error("❌ Failed to delete attendance.")
    
    st.divider()
    if st.button("📅 Show Attendance Calendar"):
        plot_attendance_calendar(student)
        

    st.divider()

    # 📌 Option to View All Students
    view_students = st.checkbox("📋 View All Students")
    
    if view_students:
        st.subheader("📊 All Student Attendance Data")

        response = requests.get(f"{API_URL}/get_all_attendance")
        if response.status_code == 200:
            student_data = response.json()
            df = pd.DataFrame(student_data)

            if not df.empty:
                df = df.sort_values(by="Roll No")  # Sort by Roll Number

                # Function to highlight students with < 75% attendance in red
                def highlight_low_attendance(row):
                    color = "background-color: red; color: white;" if row["Attendance %"] < 75 else "background-color: green; color: white;"
                    return [color] * len(row)

                # Apply styling and display dataframe
                styled_df = df.style.apply(highlight_low_attendance, axis=1)
                st.dataframe(styled_df, hide_index=True, use_container_width=True)
            else:
                st.warning("⚠ No attendance records available!")
        else:
            st.error("❌ Failed to fetch student attendance data!")

    st.divider()

    # 📌 Attendance Analysis Section for Faculty
    st.write("### 📊 **View Student's Attendance Analysis**")
    student_for_analysis = st.selectbox("Select a Student for Analysis", unique_student_list, key="analysis_student")

    if st.button("📉 Show Attendance Analysis"):
        fetch_and_plot_student_attendance(student_for_analysis)


def student_dashboard():
    st.set_page_config(page_title="ERP", page_icon="📊")
    st.title("Student Dashboard")
    student = st.session_state["username"]
    st.text(f"Name: {st.session_state['name']}")
    st.text(f"PRN: {student}")
    
    response = requests.get(f"{API_URL}/get_attendance/{student}")

    if response.status_code == 200:
        data = response.json()
        
        if not data:
            st.warning("⚠ No attendance records found!")
            return
        
        subject_attendance = {}

        for record in data:
            subject = record.get("subject", "Unknown")
            status = record.get("status", "Absent")  

            if subject == "Unknown":
                continue  

            if subject not in subject_attendance:
                subject_attendance[subject] = {"Present": 0, "Total": 0}

            subject_attendance[subject]["Total"] += 1
            if status == "Present":
                subject_attendance[subject]["Present"] += 1
        
        overall_total = sum(stats["Total"] for stats in subject_attendance.values())
        overall_present = sum(stats["Present"] for stats in subject_attendance.values())
        overall_percent = (overall_present / overall_total) * 100 if overall_total > 0 else 0

        if not subject_attendance:
            st.warning("⚠ No valid attendance records found!")
            return
        
        st.write("### 📊 **Subject-wise Attendance**")
        for subject, stats in subject_attendance.items():
            percent = (stats["Present"] / stats["Total"]) * 100 if stats["Total"] > 0 else 0
            st.write(f"**{subject}:** {percent:.2f}% ({stats['Present']}/{stats['Total']})")
        
        if overall_percent < 75:
            st.error(f"⚠️ Overall Attendance: {overall_percent:.2f}% (Defaulter)")
        else:
            st.success(f"✅ Overall Attendance: {overall_percent:.2f}% (Not Defaulter)")

        st.divider()
        if st.button("📅 Show Attendance Calendar"):
            plot_attendance_calendar(student)

        st.divider()
        
        if st.button("📉 Show Analysis"):
            plot_attendance_graph(subject_attendance, overall_present, overall_total)

    else:
        st.error("❌ Failed to fetch attendance data.")



# 📌 Function to Plot Attendance Graph for Students
def plot_attendance_graph(subject_attendance, overall_present, overall_total):
    df = pd.DataFrame(subject_attendance).T
    df["Attendance %"] = (df["Present"] / df["Total"]) * 100

    # 📊 Bar Chart for Subject-wise Attendance
    fig, ax = plt.subplots(figsize=(6, 4))
    df["Attendance %"].plot(kind="bar", ax=ax, color=["blue", "green", "red", "orange",'purple', 'cyan', 'magenta'])
    for i, value in enumerate(df["Attendance %"]):
        ax.text(i, value + 1, f"{value:.2f}%", ha='center', fontsize=10, fontweight='bold')

    ax.set_ylabel("Attendance Percentage")
    ax.set_title("📊 Subject-wise Attendance")
    st.pyplot(fig)

    # 📌 Pie Chart for Overall Attendance
    fig, ax = plt.subplots(figsize=(5, 5))
    labels = ["Present", "Absent"]
    sizes = [overall_present, overall_total - overall_present]
    colors = ["green", "red"]
    explode = (0.1, 0)  # Slightly explode the Present slice

    ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, explode=explode, startangle=90)
    ax.set_title("🏆 Overall Attendance Distribution")
    st.pyplot(fig)


# 📌 Function to Fetch & Plot Student Attendance for Faculty
def fetch_and_plot_student_attendance(student):
    response = requests.get(f"{API_URL}/get_attendance/{student}")

    
    if response.status_code == 200:
        data = response.json()
        subject_attendance = {}
        
        for record in data:
            subject = record.get("subject", "Unknown")
            status = record.get("status", "Absent")
            
            if subject not in subject_attendance:
                subject_attendance[subject] = {"Present": 0, "Total": 0}

            subject_attendance[subject]["Total"] += 1
            if status == "Present":
                subject_attendance[subject]["Present"] += 1

        overall_total = sum(stats["Total"] for stats in subject_attendance.values())
        overall_present = sum(stats["Present"] for stats in subject_attendance.values())

        plot_attendance_graph(subject_attendance, overall_present, overall_total)
    
    else:
        st.error("❌ Failed to fetch student attendance data.")


# Function to fetch attendance data
def fetch_attendance(student):
    response = requests.get(f"{API_URL}/get_attendance/{student}")
    if response.status_code == 200:
        return response.json()
    else:
        return []

# Function to plot attendance calendar
def plot_attendance_calendar(student):
    data = fetch_attendance(student)

    if not data:
        st.warning("⚠ No attendance records found!")
        return

    df = pd.DataFrame(data)
    
    if "date" not in df or "status" not in df:
        st.error("❌ Invalid data format!")
        return

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"])

    # Map attendance status to colors
    df["color"] = df["status"].map({"Present": "green", "Absent": "red"})

    # Plot calendar-style heatmap
    fig = px.scatter(df, x="date", y=[1]*len(df), color="color",
                     color_discrete_map={"green": "green", "red": "red"},
                     title=f"📅 Attendance Calendar for {student}")

    fig.update_xaxes(type="date", title="Date")
    fig.update_yaxes(visible=False)
    fig.update_layout(showlegend=False)

    st.plotly_chart(fig, use_container_width=True)



def main():
    if "username" not in st.session_state:
        login()
    elif st.session_state["role"] == "faculty":
        faculty_dashboard()
    elif st.session_state["role"] == "student":
        student_dashboard()


if __name__ == "__main__":
    main()
