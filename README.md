# 🧠 MentorMind AI

MentorMind AI is a web-based placement preparation platform designed to help students prepare for software engineering interviews.

The platform combines interview practice, coding practice, resume analysis, skill tracking, and AI-assisted evaluation into one application.

---

## 🚀 Features

### 🔐 Authentication
- User registration
- User login and logout
- Session-based authentication

### 👤 Profile Management
- View profile information
- Update name and email
- Store profile data in MySQL

### 🧠 Skill Tracking
- Add technical skills
- Select skill proficiency level
- Store skills for each user
- Display saved skills

### 🎤 Interview Practice
- Practice technical interview questions
- Submit answers
- AI-assisted interview evaluation
- Score-based feedback
- Strengths and improvement suggestions

### 💻 Coding Practice
- Python coding problems
- Execute submitted Python code
- Display execution output/errors
- Demo AI Code Coach
- Score coding solutions
- Identify strengths and improvement suggestions
- Display basic time complexity feedback

### 📄 Resume Analysis
- Upload PDF resumes
- Extract text from PDF files
- Detect technical keywords
- Generate a resume keyword score
- Store resume information in MySQL

### 📱 Responsive UI
- Desktop-friendly interface
- Mobile responsive layout
- Hamburger navigation menu
- Dark-themed interface

---

## 🛠️ Technologies Used

### Backend
- Python
- Flask
- Jinja2

### Database
- MySQL
- mysql-connector-python

### AI
- OpenAI API integration
- Rule-based demo AI evaluator for cost-free demonstration

### Resume Processing
- PyPDF2

### Frontend
- HTML
- CSS
- Responsive design

### Environment Management
- python-dotenv

---

## 🏗️ Project Structure

```text
mentormind-ai/
│
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
│
├── database/
│   └── db.py
│
├── static/
│   └── css/
│       └── style.css
│
├── templates/
│   ├── coding.html
│   ├── dashboard.html
│   ├── interview.html
│   ├── login.html
│   ├── profile.html
│   ├── register.html
│   ├── resume.html
│   ├── resume_review.html
│   └── skills.html
│
└── uploads/