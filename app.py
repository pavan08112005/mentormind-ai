from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database.db import get_db_connection

from PyPDF2 import PdfReader

import os
import uuid
import subprocess
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
# =========================================================
# APP CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "mentormind-ai-development-secret"
)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # -------------------------
        # Validation
        # -------------------------

        if not name or not email or not password:
            flash("Please fill in all fields.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash(
                "Password must contain at least 6 characters.",
                "error"
            )
            return redirect(url_for("register"))

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor()

            # Check existing email

            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(
                    "An account with this email already exists.",
                    "error"
                )

                return redirect(url_for("login"))

            # Hash password

            hashed_password = generate_password_hash(password)

            # Insert user

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password)
                VALUES (%s, %s, %s)
                """,
                (
                    name,
                    email,
                    hashed_password
                )
            )

            connection.commit()

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(url_for("login"))

        except Exception as e:

            if connection:
                connection.rollback()

            print("REGISTER ERROR:", e)

            flash(
                "Something went wrong during registration.",
                "error"
            )

            return redirect(url_for("register"))

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:

            flash(
                "Please enter email and password.",
                "error"
            )

            return redirect(url_for("login"))

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, name, email, password
                FROM users
                WHERE email = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(
                user["password"],
                password
            ):

                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]

                return redirect(url_for("dashboard"))

            flash(
                "Invalid email or password.",
                "error"
            )

            return redirect(url_for("login"))

        except Exception as e:

            print("LOGIN ERROR:", e)

            flash(
                "Unable to connect to the database.",
                "error"
            )

            return redirect(url_for("login"))

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        user_id = session["user_id"]

        # -------------------------
        # Resume
        # -------------------------

        cursor.execute(
            """
            SELECT score
            FROM resumes
            WHERE user_id = %s
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (user_id,)
        )

        resume = cursor.fetchone()

        resume_score = (
            resume["score"]
            if resume
            else 0
        )

        # -------------------------
        # Skills
        # -------------------------

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM skills
            WHERE user_id = %s
            """,
            (user_id,)
        )

        skills_result = cursor.fetchone()

        skills_count = skills_result["total"]

        return render_template(
            "dashboard.html",
            user_name=session["user_name"],
            resume_score=resume_score,
            skills_count=skills_count
        )

    except Exception as e:

        print("DASHBOARD ERROR:", e)

        return render_template(
            "dashboard.html",
            user_name=session["user_name"],
            resume_score=0,
            skills_count=0
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# PROFILE
# =========================================================

# =========================================================
# PROFILE
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        user_id = session["user_id"]

        # -----------------------------------------
        # SAVE PROFILE
        # -----------------------------------------

        if request.method == "POST":

            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()

            if not name or not email:

                flash(
                    "Name and email cannot be empty.",
                    "error"
                )

                return redirect(url_for("profile"))

            cursor.execute(
                """
                UPDATE users
                SET name = %s, email = %s
                WHERE id = %s
                """,
                (name, email, user_id)
            )

            connection.commit()

            flash(
                "Profile updated successfully.",
                "success"
            )

            return redirect(url_for("profile"))

        # -----------------------------------------
        # LOAD PROFILE
        # -----------------------------------------

        cursor.execute(
            """
            SELECT id, name, email, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        return render_template(
            "profile.html",
            user=user
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# =========================================================
# SKILLS
# =========================================================

@app.route("/skills", methods=["GET", "POST"])
def skills():

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        user_id = session["user_id"]

        if request.method == "POST":

            skill_name = request.form.get(
                "skill_name",
                ""
            ).strip()

            skill_level = request.form.get(
                "skill_level",
                "1"
            )

            if skill_name:

                cursor.execute(
                    """
                    INSERT INTO skills
                    (user_id, skill_name, skill_level)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        user_id,
                        skill_name,
                        int(skill_level)
                    )
                )

                connection.commit()

                flash(
                    "Skill added successfully.",
                    "success"
                )

        cursor.execute(
            """
            SELECT id, skill_name, skill_level
            FROM skills
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (user_id,)
        )

        user_skills = cursor.fetchall()

        return render_template(
            "skills.html",
            skills=user_skills
        )

    except Exception as e:

        if connection:
            connection.rollback()

        print("SKILLS ERROR:", e)

        flash(
            "Unable to update skills.",
            "error"
        )

        return redirect(url_for("dashboard"))

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()

# =========================================================
# DEMO AI INTERVIEW EVALUATOR
# =========================================================

def evaluate_interview_demo(question, answer):

    answer_lower = answer.lower()

    score = 0
    strengths = []
    weaknesses = []
    suggestions = []

    # -----------------------------------------------------
    # Basic answer quality
    # -----------------------------------------------------

    word_count = len(answer.split())

    if word_count >= 40:
        score += 25
        strengths.append("Your answer provides a reasonable amount of explanation.")

    elif word_count >= 20:
        score += 18
        strengths.append("Your answer gives a basic explanation.")

    elif word_count >= 10:
        score += 10
        weaknesses.append("Your answer is quite short.")

    else:
        weaknesses.append("Your answer is too short for a technical interview.")


    # -----------------------------------------------------
    # Question-specific evaluation
    # -----------------------------------------------------

    if "python" in question.lower():

        keywords = [
            "high-level",
            "programming",
            "interpreted",
            "object-oriented",
            "dynamic",
            "readable"
        ]

        found = [word for word in keywords if word in answer_lower]

        score += min(len(found) * 10, 50)

        if found:
            strengths.append(
                "You mentioned important concepts related to Python."
            )
        else:
            weaknesses.append(
                "Your answer does not mention important Python characteristics."
            )

        suggestions.append(
            "Mention that Python is a high-level, interpreted and dynamically typed programming language."
        )

        ideal_answer = (
            "Python is a high-level, interpreted and dynamically typed "
            "programming language. It is known for its simple and readable "
            "syntax and is widely used in web development, automation, "
            "data science, artificial intelligence and software development."
        )


    elif "object-oriented" in question.lower():

        keywords = [
            "class",
            "object",
            "inheritance",
            "encapsulation",
            "polymorphism",
            "abstraction"
        ]

        found = [word for word in keywords if word in answer_lower]

        score += min(len(found) * 10, 60)

        if found:
            strengths.append(
                "You mentioned concepts related to object-oriented programming."
            )
        else:
            weaknesses.append(
                "Your answer should mention classes, objects and OOP principles."
            )

        suggestions.append(
            "Explain OOP using classes, objects and principles such as inheritance, encapsulation, polymorphism and abstraction."
        )

        ideal_answer = (
            "Object-Oriented Programming is a programming approach based on "
            "objects and classes. The main principles are encapsulation, "
            "inheritance, polymorphism and abstraction."
        )


    elif "rest api" in question.lower():

        keywords = [
            "http",
            "get",
            "post",
            "put",
            "delete",
            "api",
            "client",
            "server"
        ]

        found = [word for word in keywords if word in answer_lower]

        score += min(len(found) * 10, 60)

        if found:
            strengths.append(
                "You mentioned important REST API concepts."
            )
        else:
            weaknesses.append(
                "Your answer should explain HTTP requests and client-server communication."
            )

        suggestions.append(
            "Mention HTTP methods such as GET, POST, PUT and DELETE."
        )

        ideal_answer = (
            "A REST API is an application programming interface that allows "
            "systems to communicate over HTTP. It commonly uses methods such "
            "as GET, POST, PUT and DELETE to work with resources."
        )


    elif "flask" in question.lower():

        keywords = [
            "python",
            "web",
            "framework",
            "route",
            "server",
            "application"
        ]

        found = [word for word in keywords if word in answer_lower]

        score += min(len(found) * 10, 60)

        if found:
            strengths.append(
                "You mentioned concepts related to Flask."
            )
        else:
            weaknesses.append(
                "Your answer should explain Flask as a Python web framework."
            )

        suggestions.append(
            "Mention routes, HTTP requests and Flask's role in building web applications."
        )

        ideal_answer = (
            "Flask is a lightweight Python web framework used to build "
            "web applications and APIs. It provides routing, request handling "
            "and other features required for web development."
        )


    elif "sql" in question.lower() and "nosql" in question.lower():

        keywords = [
            "relational",
            "table",
            "schema",
            "sql",
            "nosql",
            "document",
            "database"
        ]

        found = [word for word in keywords if word in answer_lower]

        score += min(len(found) * 10, 60)

        if found:
            strengths.append(
                "You identified concepts related to SQL and NoSQL databases."
            )
        else:
            weaknesses.append(
                "Your answer should compare relational and non-relational databases."
            )

        suggestions.append(
            "Explain that SQL databases are generally relational and schema-based, while NoSQL databases support flexible data models."
        )

        ideal_answer = (
            "SQL databases are generally relational databases that store data "
            "in tables with structured schemas. NoSQL databases use flexible "
            "data models such as documents, key-value pairs or graphs."
        )


    elif "list and a tuple" in question.lower():

        keywords = [
            "list",
            "tuple",
            "mutable",
            "immutable"
        ]

        found = [word for word in keywords if word in answer_lower]

        score += min(len(found) * 15, 60)

        if "mutable" in answer_lower:
            strengths.append(
                "You understand that lists can be modified."
            )

        if "immutable" in answer_lower:
            strengths.append(
                "You understand that tuples cannot be modified after creation."
            )

        if not found:
            weaknesses.append(
                "Your answer should explain mutability and the difference between lists and tuples."
            )

        suggestions.append(
            "Clearly mention that lists are mutable while tuples are immutable."
        )

        ideal_answer = (
            "A list is a mutable Python collection, meaning its elements can "
            "be changed after creation. A tuple is immutable, meaning its "
            "elements cannot be changed after creation."
        )


    elif "inheritance" in question.lower():

        keywords = [
            "class",
            "parent",
            "child",
            "inherit",
            "method",
            "property"
        ]

        found = [word for word in keywords if word in answer_lower]

        score += min(len(found) * 10, 60)

        if found:
            strengths.append(
                "You mentioned concepts related to inheritance."
            )
        else:
            weaknesses.append(
                "Your answer should explain parent and child classes."
            )

        suggestions.append(
            "Use a simple parent-class and child-class example when explaining inheritance."
        )

        ideal_answer = (
            "Inheritance is an OOP concept where a child class can inherit "
            "properties and methods from a parent class. It promotes code "
            "reuse and allows classes to extend existing functionality."
        )


    elif "encapsulation" in question.lower():

        keywords = [
            "data",
            "class",
            "method",
            "private",
            "protect",
            "hide"
        ]

        found = [word for word in keywords if word in answer_lower]

        score += min(len(found) * 10, 60)

        if found:
            strengths.append(
                "You mentioned concepts related to data protection and encapsulation."
            )
        else:
            weaknesses.append(
                "Your answer should explain how data and methods are bundled together."
            )

        suggestions.append(
            "Explain encapsulation as bundling data and methods together and controlling access to the data."
        )

        ideal_answer = (
            "Encapsulation is an OOP principle that combines data and the "
            "methods that operate on that data inside a class. It also helps "
            "control access to internal data."
        )


    else:

        ideal_answer = (
            "Give a clear definition, explain the main concept and provide "
            "a simple example."
        )


    # -----------------------------------------------------
    # Final score
    # -----------------------------------------------------

    score = min(score, 100)

    if score >= 80:
        strengths.append(
            "Overall, your answer is strong for an interview response."
        )

    elif score >= 60:
        suggestions.append(
            "Add more technical details to make your answer stronger."
        )

    else:
        weaknesses.append(
            "The answer needs more technical explanation."
        )

        suggestions.append(
            "Try answering with a definition, key points and a simple example."
        )


    # -----------------------------------------------------
    # Create feedback
    # -----------------------------------------------------

    feedback = f"""
SCORE: {score}/100

STRENGTHS:
"""

    if strengths:
        for item in strengths:
            feedback += f"- {item}\n"
    else:
        feedback += "- More explanation is needed.\n"


    feedback += """
WEAKNESSES:
"""

    if weaknesses:
        for item in weaknesses:
            feedback += f"- {item}\n"
    else:
        feedback += "- No major weaknesses detected.\n"


    feedback += """
SUGGESTIONS:
"""

    for item in suggestions:
        feedback += f"- {item}\n"


    feedback += f"""
IDEAL ANSWER:

{ideal_answer}
"""

    return score, feedback
# =========================================================
# INTERVIEW
# =========================================================


@app.route("/interview", methods=["GET", "POST"])
def interview():

    if "user_id" not in session:
        return redirect(url_for("login"))

    questions = [
        {
            "id": 1,
            "question": "What is Python?"
        },
        {
            "id": 2,
            "question": "What is Object-Oriented Programming?"
        },
        {
            "id": 3,
            "question": "What is a REST API?"
        },
        {
            "id": 4,
            "question": "What is Flask?"
        },
        {
            "id": 5,
            "question": "What is the difference between SQL and NoSQL?"
        },
        {
            "id": 6,
            "question": "Explain the difference between a list and a tuple in Python."
        },
        {
            "id": 7,
            "question": "What is inheritance?"
        },
        {
            "id": 8,
            "question": "What is encapsulation?"
        }
    ]

    # =====================================================
    # ANSWER SUBMISSION
    # =====================================================

    if request.method == "POST":

        question_id = request.form.get("question_id")

        answer = request.form.get(
            "answer",
            ""
        ).strip()

        if not answer:

            flash(
                "Please write an answer before submitting.",
                "error"
            )

            return redirect(
                url_for("interview")
            )

        # =================================================
        # FIND SELECTED QUESTION
        # =================================================

        selected_question = None

        for question in questions:

            if str(question["id"]) == str(question_id):

                selected_question = question

                break

        if selected_question is None:

            flash(
                "Invalid question.",
                "error"
            )

            return redirect(
                url_for("interview")
            )

        # =================================================
        # LOCAL AI DEMO EVALUATION
        # =================================================

        score, feedback = evaluate_interview_demo(
            selected_question["question"],
            answer
        )

        # =================================================
        # DISPLAY RESULT
        # =================================================

        return render_template(
            "interview.html",

            questions=questions,

            result=True,

            submitted_question=
                selected_question["question"],

            score=score,

            feedback=feedback
        )

    # =====================================================
    # FIRST PAGE LOAD
    # =====================================================

    return render_template(
        "interview.html",

        questions=questions,

        result=False
    )
# =========================================================
# DEMO AI CODE EVALUATOR
# =========================================================

def evaluate_code_demo(question_id, code, success, output):

    code_lower = code.lower()

    score = 0
    strengths = []
    suggestions = []

    # -----------------------------------------
    # Execution
    # -----------------------------------------

    if success:

        score += 30

        strengths.append(
            "Your code executed successfully."
        )

    else:

        suggestions.append(
            "Fix the execution error before optimizing the solution."
        )


    # -----------------------------------------
    # Question-specific evaluation
    # -----------------------------------------

    if question_id == "1":

        # Reverse a String

        if "[::-1]" in code:
            score += 30
            strengths.append(
                "You used Python string slicing effectively."
            )

        elif "reverse" in code_lower:
            score += 20
            strengths.append(
                "Your code appears to use a reversing approach."
            )

        else:
            suggestions.append(
                "Consider using string slicing or a loop to reverse the string."
            )

        if "for " in code_lower:

            score += 15

            strengths.append(
                "You used iteration in your solution."
            )

        suggestions.append(
            "Make sure your solution handles an empty string."
        )

        complexity = "O(n) time"


    elif question_id == "2":

        # Find Maximum Number

        if "max(" in code_lower:

            score += 30

            strengths.append(
                "You used Python's built-in max() function."
            )

        elif "for " in code_lower:

            score += 25

            strengths.append(
                "You used iteration to examine the numbers."
            )

        else:

            suggestions.append(
                "Use a loop or max() to find the largest value."
            )

        if ">" in code:

            score += 15

            strengths.append(
                "Your solution uses comparison logic."
            )

        suggestions.append(
            "Consider how your solution behaves with an empty list."
        )

        complexity = "O(n) time"


    elif question_id == "3":

        # Palindrome

        if "[::-1]" in code:

            score += 30

            strengths.append(
                "You used string slicing to reverse the value."
            )

        elif "reverse" in code_lower:

            score += 20

            strengths.append(
                "Your solution includes a reversing approach."
            )

        else:

            suggestions.append(
                "Compare the original string with its reversed form."
            )

        if "==" in code:

            score += 15

            strengths.append(
                "You used comparison logic."
            )

        suggestions.append(
            "Consider converting the input consistently before comparison."
        )

        complexity = "O(n) time"


    elif question_id == "4":

        # Count Vowels

        vowel_list = ["a", "e", "i", "o", "u"]

        found_vowels = 0

        for vowel in vowel_list:

            if vowel in code_lower:

                found_vowels += 1

        if found_vowels >= 3:

            score += 30

            strengths.append(
                "Your solution includes vowel-related logic."
            )

        else:

            suggestions.append(
                "Make sure your code checks all five vowels."
            )

        if "for " in code_lower:

            score += 20

            strengths.append(
                "You used iteration."
            )

        suggestions.append(
            "Consider handling both uppercase and lowercase vowels."
        )

        complexity = "O(n) time"


    else:

        suggestions.append(
            "Try to explain your algorithm and edge cases."
        )

        complexity = "Depends on the solution"


    # -----------------------------------------
    # Code quality
    # -----------------------------------------

    if len(code.splitlines()) <= 15:

        score += 10

        strengths.append(
            "Your solution is reasonably concise."
        )

    else:

        suggestions.append(
            "Consider simplifying the solution if possible."
        )


    # -----------------------------------------
    # Final score
    # -----------------------------------------

    score = min(score, 100)


    # -----------------------------------------
    # Default feedback
    # -----------------------------------------

    if not strengths:

        strengths.append(
            "You attempted a solution to the problem."
        )

    if not suggestions:

        suggestions.append(
            "Consider adding comments and handling edge cases."
        )


    if score >= 80:

        overall = "Excellent solution!"

    elif score >= 60:

        overall = "Good solution with some room for improvement."

    else:

        overall = "Your solution needs improvement."


    return {
        "score": score,
        "overall": overall,
        "strengths": strengths,
        "suggestions": suggestions,
        "complexity": complexity
    }
# =========================================================
# CODING
# =========================================================

@app.route("/coding", methods=["GET", "POST"])
def coding():

    if "user_id" not in session:
        return redirect(url_for("login"))

    questions = [

    {
        "id": 1,
        "title": "Reverse a String",
        "description": "Write a Python program to reverse a given string.",
        "test_cases": [
            {"input": "hello", "expected": "olleh"},
            {"input": "python", "expected": "nohtyp"},
            {"input": "MentorMind", "expected": "dniMrotneM"}
        ]
    },

    {
        "id": 2,
        "title": "Find Maximum Number",
        "description": "Write a Python program to find the maximum number in a list.",
        "test_cases": [
            {"input": "[1, 5, 3, 9, 2]", "expected": "9"},
            {"input": "[10, 20, 5, 8]", "expected": "20"},
            {"input": "[-5, -2, -10]", "expected": "-2"}
        ]
    },

    {
        "id": 3,
        "title": "Check Palindrome",
        "description": "Write a Python program to check whether a string is a palindrome.",
        "test_cases": [
            {"input": "madam", "expected": "True"},
            {"input": "hello", "expected": "False"},
            {"input": "level", "expected": "True"}
        ]
    },

    {
        "id": 4,
        "title": "Count Vowels",
        "description": "Write a Python program to count the number of vowels in a string.",
        "test_cases": [
            {"input": "hello", "expected": "2"},
            {"input": "python", "expected": "1"},
            {"input": "MentorMind AI", "expected": "5"}
        ]
    }

]
    if request.method == "POST":

        code = request.form.get("code", "").strip()

        if not code:
            flash("Please enter Python code.", "error")

            return redirect(url_for("coding"))

        try:

            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    code
                ],
                capture_output=True,
                text=True,
                timeout=5
            )

            output = result.stdout

            if result.stderr:
                output += "\n" + result.stderr

            success = result.returncode == 0

        except subprocess.TimeoutExpired:

            output = "Code execution timed out."

            success = False

        except Exception as e:

            output = str(e)

            success = False

                # -----------------------------------------
        # DEMO AI CODE EVALUATION
        # -----------------------------------------

        question_id = request.form.get("question_id", "1")

        ai_feedback = evaluate_code_demo(
            question_id,
            code,
            success,
            output
        )

        return render_template(
            "coding.html",
            questions=questions,
            result=True,
            output=output,
            success=success,
            ai_feedback=ai_feedback
        )

    return render_template(
        "coding.html",
        questions=questions,
        result=False
    )
# =========================================================
# RESUME
# =========================================================

@app.route("/resume", methods=["GET", "POST"])
def resume():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        file = request.files.get("resume")

        if not file or file.filename == "":
            flash("Please select a PDF file.", "error")
            return redirect(url_for("resume"))

        if not file.filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.", "error")
            return redirect(url_for("resume"))

        safe_filename = secure_filename(file.filename)

        unique_filename = (
            str(uuid.uuid4()) + "_" + safe_filename
        )

        upload_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "uploads"
        )

        os.makedirs(
            upload_folder,
            exist_ok=True
        )

        file_path = os.path.join(
            upload_folder,
            unique_filename
        )

        # Save PDF
        file.save(file_path)

        # =================================================
        # EXTRACT TEXT FROM PDF
        # =================================================

        resume_text = ""

        try:

            reader = PdfReader(file_path)

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    resume_text += text + "\n"

        except Exception as e:

            print("PDF EXTRACTION ERROR:", e)

            flash(
                "Unable to read the PDF.",
                "error"
            )

            return redirect(url_for("resume"))

        # =================================================
        # RESUME KEYWORD ANALYSIS
        # =================================================

        text_lower = resume_text.lower()

        keywords = [
            "python",
            "java",
            "sql",
            "mysql",
            "flask",
            "django",
            "html",
            "css",
            "javascript",
            "git",
            "github",
            "rest api",
            "machine learning",
            "artificial intelligence",
            "ai",
            "data structures",
            "algorithms",
            "c",
            "c++",
            "react",
            "mongodb"
        ]

        found_keywords = []

        for keyword in keywords:

            if keyword.lower() in text_lower:
                found_keywords.append(keyword)

        # =================================================
        # SCORE
        # =================================================

        total_keywords = len(keywords)

        if total_keywords > 0:

            score = int(
                (len(found_keywords) / total_keywords) * 100
            )

        else:

            score = 0

        # =================================================
        # SAVE TO MYSQL
        # =================================================

        connection = None
        cursor = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO resumes
                (
                    user_id,
                    file_name,
                    file_path,
                    score
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    safe_filename,
                    file_path,
                    score
                )
            )

            connection.commit()

        except Exception as e:

            if connection:
                connection.rollback()

            print("RESUME DATABASE ERROR:", e)

            flash(
                "Resume was analyzed but could not be saved.",
                "error"
            )

            return redirect(url_for("resume"))

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

        return render_template(
            "resume_review.html",
            score=score,
            keywords=found_keywords,
            resume_text=resume_text,
            file_name=safe_filename
        )

    return render_template("resume.html")


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return {
        "status": "ok",
        "application": "MentorMind AI"
    }

# =========================================================
# TEMPORARY DATABASE TEST
# =========================================================

@app.route("/db-test")
def db_test():

    import socket

    host = os.getenv("DB_HOST")
    port = int(os.getenv("DB_PORT", "3306"))

    # Test DNS
    try:
        ip = socket.gethostbyname(host)
    except Exception as e:
        return {
            "status": "FAILED",
            "stage": "DNS",
            "error": str(e)
        }, 500

    # Test TCP connection
    try:
        sock = socket.create_connection(
            (host, port),
            timeout=10
        )
        sock.close()
    except Exception as e:
        return {
            "status": "FAILED",
            "stage": "TCP",
            "host": host,
            "port": port,
            "resolved_ip": ip,
            "error": str(e)
        }, 500

    # Test MySQL
    try:

        connection = get_db_connection()

        connection.close()

        return {
            "status": "SUCCESS",
            "message": "Render can connect to Aiven MySQL.",
            "resolved_ip": ip
        }

    except Exception as e:

        return {
            "status": "FAILED",
            "stage": "MYSQL",
            "error": str(e)
        }, 500
# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )