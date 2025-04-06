from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_cors import CORS


app = Flask(__name__)
CORS(app)  # Enable CORS

# ✅ Define MongoDB URI
app.config["MONGO_URI"] = "mongodb://localhost:27017/attendance_db"
mongo = PyMongo(app)

db = mongo.db       # database
users = db.users    # users collection
attendance = db.attendance  # attendance collection

# ✅ Delete existing users & attendance to reset the database
# users.delete_many({})
# attendance.delete_many({})

# ✅ Faculty-Subject Mapping
faculty_subjects = {
    "Kavita Patil": "DAA",
    "Kirti Deshpande": "DBMS",
    "Neeraj Sathawane": "DAV",
    "Suhasini Bhat": "BCVS",
    "Raj": "CT",
    "Kavita Moholkar": "IPR"
}

# ✅ Default Users
default_users = [
    # Faculty Users
    {"username": "kavitapatil", "password": "pass123", "role": "faculty", "name": "Kavita Patil"},
    {"username": "kirtideshpande", "password": "pass123", "role": "faculty", "name": "Kirti Deshpande"},
    {"username": "neerajsathawane", "password": "pass123", "role": "faculty", "name": "Neeraj Sathawane"},
    {"username": "suhasinibhat", "password": "pass123", "role": "faculty", "name": "Suhasini Bhat"},
    {"username": "raj", "password": "pass123", "role": "faculty", "name": "Raj"},
    {"username": "kavitamoholkar", "password": "pass123", "role": "faculty", "name": "Kavita Moholkar"},

    # Student Users with Roll Numbers
    {"username": "RBT23CB001", "password": "pass123", "role": "student", "name": "Pramay Wankhade"},
    {"username": "RBT23CB002", "password": "pass123", "role": "student", "name": "Student 2"},
    {"username": "RBT23CB003", "password": "pass123", "role": "student", "name": "Student 3"},
    {"username": "RBT23CB004", "password": "pass123", "role": "student", "name": "Student 4"},
    {"username": "RBT23CB005", "password": "pass123", "role": "student", "name": "Student 5"}
]

# ✅ Inserting the default users into the database
users.insert_many(default_users)
print("✅ Users inserted successfully!")


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = users.find_one({"username": data["username"], "password": data["password"]}, {"_id": 0})
    if user:
        return jsonify(user), 200
    return jsonify({"message": "Invalid Credentials"}), 401


@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    data = request.json

    if "faculty" not in data:  
        return jsonify({"message": "Unauthorized - Only faculty can mark attendance"}), 403

    faculty_name = users.find_one({"username": data["faculty"]}, {"_id": 0, "name": 1})
    
    if not faculty_name:
        return jsonify({"message": "Invalid Faculty"}), 403

    faculty_name = faculty_name["name"]
    subject = faculty_subjects.get(faculty_name, "Unknown")  # Get subject from mapping

    try:
        attendance.insert_one({
            "student": data["student"],
            "date": data["date"],
            "status": data["status"],
            "marked_by": data["faculty"],
            "subject": subject  # ✅ Store Subject in Attendance Records
        })
        return jsonify({"message": "Attendance marked successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Failed to update attendance", "error": str(e)}), 500



@app.route('/get_attendance/<student>', methods=['GET'])
def get_attendance(student):
    try:
        records = list(attendance.find({"student": student}, {"_id": 0}))
        return jsonify(records), 200
    except Exception as e:
        return jsonify({"message": "Failed to fetch attendance", "error": str(e)}), 500

@app.route('/get_students', methods=['GET'])
def get_students():
    try:
        # Fetch only student users from the database
        student_list = list(users.find({"role": "student"}, {"_id": 0, "username": 1}))

        # Extract usernames
        student_usernames = [student["username"] for student in student_list]

        return jsonify(student_usernames), 200
    except Exception as e:
        return jsonify({"message": "Failed to fetch students", "error": str(e)}), 500

# Get all student attendance
@app.route('/get_all_attendance', methods=['GET'])
def get_all_attendance():
    try:
        # Fetch distinct students
        student_list = users.find({"role": "student"}, {"_id": 0, "username": 1, "name": 1})
        
        attendance_data = []  # Store final data

        unique_students = set()  # ✅ Prevent duplicates

        for student in student_list:
            student_id = student["username"]
            student_name = student["name"]

            # ✅ Ensure uniqueness before processing
            if student_id in unique_students:
                continue  # Skip duplicate entries
            unique_students.add(student_id)

            # Count total attendance records for this student
            total_classes = attendance.count_documents({"student": student_id})

            # Count present days for this student
            present_days = attendance.count_documents({"student": student_id, "status": "Present"})

            # Calculate attendance percentage
            attendance_percentage = (present_days / total_classes) * 100 if total_classes > 0 else 0

            # Append the student data
            attendance_data.append({
                "Roll No": student_id,
                "Name": student_name,
                "Total Classes": total_classes,
                "Present Days": present_days,
                "Attendance %": round(attendance_percentage, 2)
            })

        return jsonify(attendance_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete_attendance", methods=["POST"])
def delete_attendance():
    data = request.json
    student = data.get("student")
    date = data.get("date")
    
    if not student or not date:
        return jsonify({"error": "Student and date are required"}), 400

    result = attendance.delete_one({"student": student, "date": date})

    if result.deleted_count > 0:
        return jsonify({"message": "Attendance deleted successfully"}), 200
    else:
        return jsonify({"error": "No matching record found"}), 404



if __name__ == '__main__':
    app.run(debug=True)
