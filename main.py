# backend/main.py
# Main FastAPI application that mounts all routers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# Import all routers
from .auth import router as auth_router
from .marksheet_router import router as marksheet_router
from .quiz_router import router as quiz_router
from .resume_router import router as resume_router
from .student_router import router as student_router
from .admin_router import router as admin_router

# Create main app
app = FastAPI(
    title="SkillSync - AI Placement Copilot",
    description="Complete platform with authentication, marksheet extraction, resume analysis, and adaptive quizzes",
    version="1.0.0"
)

# CORS middleware for frontend (localhost:5173 for Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(auth_router)          # /auth/*
app.include_router(student_router)       # /student/*
app.include_router(admin_router)         # /admin/*
app.include_router(marksheet_router)     # /marksheet/*
app.include_router(quiz_router)          # /quiz/*
app.include_router(resume_router)        # /resume/*

# Root endpoint
@app.get("/", response_class=HTMLResponse)
def root():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>SkillSync - AI Placement Copilot</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1000px;
                margin: 40px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 12px;
                padding: 40px;
                color: #333;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 {
                color: #667eea;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
            }
            h2 {
                color: #764ba2;
                margin-top: 30px;
            }
            .endpoint-group {
                background: #f8f9fa;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .endpoint {
                font-family: 'Courier New', monospace;
                background: #e9ecef;
                padding: 8px 12px;
                margin: 5px 0;
                border-radius: 4px;
                display: block;
            }
            .method {
                font-weight: bold;
                color: #28a745;
                margin-right: 10px;
            }
            .method.post { color: #ffc107; }
            .method.delete { color: #dc3545; }
            a {
                color: #667eea;
                text-decoration: none;
                font-weight: bold;
            }
            a:hover {
                text-decoration: underline;
            }
            .badge {
                background: #667eea;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                margin-left: 8px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎓 SkillSync - AI Placement Copilot</h1>
            <p>Welcome to SkillSync, the complete AI-powered placement preparation platform for students.</p>
            
            <h2>📚 Features</h2>
            <ul>
                <li><strong>Marksheet Extraction</strong>: Upload PDF marksheets and auto-extract GPAs, CGPA, and percentages</li>
                <li><strong>Resume Analyzer</strong>: Match your resume against job descriptions and get improvement roadmaps</li>
                <li><strong>Adaptive Quiz</strong>: Take personalized quizzes that adapt to your skill level</li>
                <li><strong>Role-Based Access</strong>: Student and Admin dashboards with secure JWT authentication</li>
            </ul>

            <h2>🔐 Authentication</h2>
            <div class="endpoint-group">
                <code class="endpoint"><span class="method post">POST</span> /auth/signup</code>
                <code class="endpoint"><span class="method post">POST</span> /auth/login</code>
                <code class="endpoint"><span class="method">GET</span> /auth/me <span class="badge">Protected</span></code>
            </div>

            <h2>👨‍🎓 Student Endpoints</h2>
            <div class="endpoint-group">
                <code class="endpoint"><span class="method">GET</span> /student/dashboard/ <span class="badge">Protected</span></code>
                <code class="endpoint"><span class="method post">POST</span> /student/upload-marksheet/ <span class="badge">Protected</span></code>
                <code class="endpoint"><span class="method post">POST</span> /student/upload-resume/ <span class="badge">Protected</span></code>
                <code class="endpoint"><span class="method">GET</span> /student/quiz/generate <span class="badge">Protected</span></code>
                <code class="endpoint"><span class="method post">POST</span> /student/quiz/submit <span class="badge">Protected</span></code>
                <code class="endpoint"><span class="method">GET</span> /student/quiz/dashboard <span class="badge">Protected</span></code>
            </div>

            <h2>👨‍💼 Admin Endpoints</h2>
            <div class="endpoint-group">
                <code class="endpoint"><span class="method">GET</span> /admin/users/ <span class="badge">Admin Only</span></code>
                <code class="endpoint"><span class="method">GET</span> /admin/user/{user_id} <span class="badge">Admin Only</span></code>
                <code class="endpoint"><span class="method delete">DELETE</span> /admin/user/{user_id} <span class="badge">Admin Only</span></code>
                <code class="endpoint"><span class="method">GET</span> /admin/stats/ <span class="badge">Admin Only</span></code>
                <code class="endpoint"><span class="method">GET</span> /admin/settings/ <span class="badge">Admin Only</span></code>
            </div>

            <h2>📄 Public Endpoints</h2>
            <div class="endpoint-group">
                <code class="endpoint"><span class="method">GET</span> /marksheet/students/</code>
                <code class="endpoint"><span class="method post">POST</span> /resume/analyze/</code>
                <code class="endpoint"><span class="method post">POST</span> /quiz/seed-sample-questions/</code>
            </div>

            <h2>📖 Documentation</h2>
            <p>
                <a href="/docs" target="_blank">📘 Interactive API Docs (Swagger UI)</a><br>
                <a href="/redoc" target="_blank">📗 Alternative Docs (ReDoc)</a>
            </p>

            <h2>🚀 Quick Start</h2>
            <ol>
                <li>Create an admin user: <code>python -m backend.seed_admin</code></li>
                <li>Start frontend: <code>cd frontend && npm run dev</code></li>
                <li>Login at <a href="http://localhost:5173">http://localhost:5173</a></li>
            </ol>

            <p style="margin-top: 40px; text-align: center; color: #6c757d;">
                <small>SkillSync v1.0.0 | Built with FastAPI & React</small>
            </p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "SkillSync API",
        "version": "1.0.0",
        "databases": {
            "auth": "auth.db",
            "marksheets": "marksheets.db",
            "quiz": "quiz.db"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

