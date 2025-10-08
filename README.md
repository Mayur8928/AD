# 🎓 SkillSync - AI Placement Copilot

**SkillSync** is a comprehensive AI-powered placement preparation platform designed to help students analyze their academic performance, optimize their resumes, and enhance their skills through adaptive quizzes.

![SkillSync](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

## ✨ Features

### 📚 **Marksheet Extractor**
- Upload PDF marksheets and automatically extract:
  - Semester-wise GPA and CGPA
  - Percentage calculations
  - Academic year information
  - Subject-wise breakdown

### 📄 **Resume Analyzer**
- AI-powered resume analysis against job descriptions
- Skill matching with semantic similarity
- Gap identification and missing skills detection
- Personalized improvement roadmap
- Experience extraction and validation

### 🧠 **Adaptive Quiz System**
- Topic-based adaptive questioning (Python, SQL, Logic, Quant, Language, Statistics)
- Difficulty adjustment based on performance
- Weak area identification and focused practice
- Real-time performance tracking
- Historical analytics and trend visualization

### 👥 **Role-Based Access Control**
- **Student Dashboard**: Personal progress tracking, file uploads, quiz taking
- **Admin Dashboard**: User management, comprehensive analytics, settings control
- JWT-based secure authentication
- Protected API endpoints

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (for backend)
- **Node.js 16+** (for frontend)
- **pip** (Python package manager)
- **npm** or **yarn** (Node package manager)

### Backend Setup

1. **Navigate to project directory:**
```bash
cd E:\AD
```

2. **Install Python dependencies:**
```bash
pip install -r backend/requirements.txt
```

3. **Create admin user (for testing):**
```bash
python -m backend.seed_admin
```

This creates an admin user with:
- Email: `admin@skillsync.local`
- Password: `admin123`

4. **Start the backend server:**
```bash
uvicorn backend.main:app --reload --port 8000
```

The backend API will be available at: **http://localhost:8000**

### Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

3. **Start the development server:**
```bash
npm run dev
```

The frontend will be available at: **http://localhost:5173**

## 📖 Usage Guide

### For Students

1. **Sign Up**: Create an account at `/signup` with your email, name, SAP number, and password
2. **Login**: Access your dashboard at `/login`
3. **Dashboard**: View your academic performance, quiz scores, and resume analysis
4. **Upload Marksheet**: Upload semester PDF marksheets for automatic extraction
5. **Analyze Resume**: Upload your resume with an optional job description for AI-powered analysis
6. **Take Quiz**: Start an adaptive quiz that adjusts to your skill level
7. **Track Progress**: Monitor your performance over time with detailed analytics

### For Admins

1. **Login**: Use admin credentials at `/login`
2. **View Users**: Access all registered students at `/admin/users`
3. **User Details**: Click on any student to view:
   - Uploaded files
   - Marksheet history
   - Quiz performance
   - Overall progress
4. **Manage Users**: Delete users or reprocess marksheets
5. **Configure Settings**: Adjust quiz difficulty thresholds and adaptive parameters

## 🏗️ Architecture

### Backend (FastAPI)

```
backend/
├── main.py                 # Main FastAPI app, router mounting
├── auth.py                 # JWT authentication, user management
├── marksheet_router.py     # Marksheet PDF extraction
├── quiz_router.py          # Adaptive quiz logic
├── resume_router.py        # Resume analysis with AI
├── student_router.py       # Student-specific endpoints
├── admin_router.py         # Admin-only endpoints
├── seed_admin.py           # Admin user creation script
└── requirements.txt        # Python dependencies
```

**Databases** (SQLite):
- `auth.db`: User authentication and file metadata
- `marksheets.db`: Academic records
- `quiz.db`: Quiz questions and results

### Frontend (React + Vite)

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.jsx               # Login page
│   │   ├── Signup.jsx              # Registration page
│   │   ├── StudentDashboard.jsx    # Student main dashboard
│   │   ├── UploadMarksheet.jsx     # Marksheet upload
│   │   ├── UploadResume.jsx        # Resume analyzer
│   │   ├── QuizPage.jsx            # Adaptive quiz interface
│   │   ├── AdminUsers.jsx          # Admin user list
│   │   └── AdminUserDetail.jsx     # Admin user details
│   ├── components/
│   │   ├── Navbar.jsx              # Navigation bar
│   │   └── ProtectedRoute.jsx      # Route authentication
│   ├── context/
│   │   └── AuthContext.jsx         # Auth state management
│   ├── utils/
│   │   └── api.js                  # Axios API client
│   ├── App.jsx                     # Main app & routing
│   ├── main.jsx                    # React entry point
│   └── index.css                   # Global styles (Tailwind)
├── package.json
└── vite.config.js
```

## 🔐 API Endpoints

### Authentication
- `POST /auth/signup` - Register new student
- `POST /auth/login` - User login (returns JWT)
- `GET /auth/me` - Get current user (protected)

### Student Endpoints (Protected)
- `GET /student/dashboard/` - Student dashboard data
- `POST /student/upload-marksheet/` - Upload marksheet PDF
- `POST /student/upload-resume/` - Analyze resume
- `GET /student/quiz/generate` - Generate adaptive quiz
- `POST /student/quiz/submit` - Submit quiz answers
- `GET /student/quiz/dashboard` - Quiz analytics

### Admin Endpoints (Admin-Only)
- `GET /admin/users/` - List all students
- `GET /admin/user/{user_id}` - Get user details
- `DELETE /admin/user/{user_id}` - Delete user
- `GET /admin/stats/` - Platform statistics
- `GET /admin/settings/` - Get quiz settings
- `POST /admin/settings/update` - Update settings

### Public Endpoints
- `POST /quiz/seed-sample-questions/` - Seed quiz database
- `GET /health` - Health check

**API Documentation**: http://localhost:8000/docs

## 🎨 Design & UI

The application features a modern, aesthetic design with:

- **Gradient backgrounds** with purple/pink themes
- **Glass morphism** effects for cards
- **Smooth animations** and transitions
- **Responsive design** for all screen sizes
- **Interactive charts** for analytics
- **Beautiful color schemes** for different user roles
- **Intuitive navigation** with clear visual hierarchy

Built with **Tailwind CSS** for utility-first styling and **Lucide React** for beautiful icons.

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory (optional):

```env
GEMINI_API_KEY=your_gemini_api_key_here  # For AI roadmap generation
EMBED_MODEL=all-MiniLM-L6-v2             # Sentence transformer model
```

### Quiz Settings (Admin Configurable)

- `promote_threshold`: 0.7 (70% accuracy to increase difficulty)
- `demote_threshold`: 0.4 (40% accuracy to decrease difficulty)
- `weak_topic_threshold`: 0.5 (50% accuracy to identify weak areas)
- `weak_share_fraction`: 0.30 (30% questions from weak topics)
- `lookback_quizzes`: 6 (number of recent quizzes to analyze)
- `weak_lookback`: 3 (quizzes to check for weak topics)

## 📊 Database Schema

### auth.db
```sql
users (id, email, password_hash, sap_no, full_name, role, created_at)
user_files (id, user_id, file_type, filename, uploaded_at)
```

### marksheets.db
```sql
students (id, student_name, sap_no)
marksheets (id, student_id, semester, academic_year, sem_gpa, sem_cgpa, percentage, ...)
```

### quiz.db
```sql
students (id, student_name, sap_no)
quiz_questions (id, topic, difficulty, question, options, correct_option)
quiz_results (id, student_id, score, total, scores_json, taken_at)
app_settings (key, value)
```

## 🧪 Testing

### Initial Setup for Demo

1. Start backend and frontend servers
2. Create admin user: `python -m backend.seed_admin`
3. Seed quiz questions:
   ```bash
   curl -X POST http://localhost:8000/quiz/seed-sample-questions/
   ```
4. Login as admin: `admin@skillsync.local` / `admin123`
5. Create a student account via signup
6. Upload sample marksheet PDFs
7. Take adaptive quiz
8. Analyze resume

### Sample Test Flow

**Student Journey:**
1. Sign up with email and SAP number
2. Upload Semester 1 marksheet PDF
3. View extracted GPA/CGPA on dashboard
4. Upload resume with job description
5. Review skill gaps and improvement roadmap
6. Take adaptive quiz (12 questions)
7. View quiz results and analytics
8. Take another quiz to see difficulty adaptation

**Admin Journey:**
1. Login as admin
2. View platform statistics
3. Browse all students
4. Click on a student to see details
5. Review their marksheets, quiz history
6. Adjust quiz settings if needed

## 🤝 Contributing

This project is designed for academic/placement preparation purposes. Contributions are welcome!

## 📝 License

This project is for educational purposes. Feel free to use and modify as needed.

## 🙏 Acknowledgments

- **FastAPI** for the robust backend framework
- **React** + **Vite** for the blazing-fast frontend
- **Tailwind CSS** for beautiful, responsive design
- **Sentence Transformers** for semantic analysis
- **Google Gemini** for AI-powered roadmaps
- **pdfplumber** for PDF text extraction

## 📞 Support

For issues or questions, please check:
- API Documentation: http://localhost:8000/docs
- Frontend Dev Tools: Browser console
- Backend Logs: Terminal output

---

**Built with ❤️ for students preparing for placements**

## 🚦 Project Status

✅ **Completed Features:**
- JWT Authentication with role-based access
- Marksheet PDF extraction and analysis
- Resume-to-JD matching with AI
- Adaptive quiz with difficulty adjustment
- Student and Admin dashboards
- Beautiful, modern UI with Tailwind CSS
- Comprehensive API with FastAPI
- Real-time analytics and visualizations

🎯 **Future Enhancements:**
- AI Chatbot for mentoring
- Company-specific preparation modules
- Interview scheduling and tracking
- Collaborative study groups
- Mobile app (React Native)

