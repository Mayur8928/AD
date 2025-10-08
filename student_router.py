# backend/student_router.py
# Student-specific protected endpoints
import sqlite3
from typing import Dict, Any
from fastapi import APIRouter, Depends, File, UploadFile, Form
from fastapi.responses import JSONResponse
from .auth import get_current_user

router = APIRouter(prefix="/student", tags=["Student"])

# ============= Helper to get quiz student_id from user =============
def get_or_create_quiz_student(user_id: int, sap_no: str, full_name: str) -> int:
    """
    Ensure quiz.db has a student record for this user.
    Maps auth user to quiz student via SAP number.
    """
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    
    # Try to find by SAP
    if sap_no:
        c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
        row = c.fetchone()
        if row:
            conn.close()
            return row[0]
    
    # Create new quiz student
    c.execute("INSERT INTO students (student_name, sap_no) VALUES (?, ?)", (full_name, sap_no))
    conn.commit()
    student_id = c.lastrowid
    conn.close()
    return student_id

def get_or_create_marksheet_student(sap_no: str, full_name: str) -> int:
    """
    Ensure marksheets.db has a student record.
    """
    conn = sqlite3.connect("marksheets.db")
    c = conn.cursor()
    
    if sap_no:
        c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
        row = c.fetchone()
        if row:
            conn.close()
            return row[0]
    
    c.execute("INSERT INTO students (student_name, sap_no) VALUES (?, ?)", (full_name, sap_no))
    conn.commit()
    student_id = c.lastrowid
    conn.close()
    return student_id

# ============= Student Dashboard Endpoint =============
@router.get("/dashboard/")
async def student_dashboard(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Combined student dashboard showing:
    - Marksheet summary
    - Last resume analysis (if any)
    - Quiz dashboard summary
    """
    user_id = current_user["id"]
    sap_no = current_user.get("sap_no") or ""
    full_name = current_user.get("full_name") or "Student"
    
    # Get marksheet data
    marksheet_data = {"semesters": [], "cumulative_cgpa": None, "overall_percentage": None}
    if sap_no:
        conn = sqlite3.connect("marksheets.db")
        c = conn.cursor()
        c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
        student_row = c.fetchone()
        if student_row:
            student_id = student_row[0]
            c.execute("""
                SELECT semester, sem_gpa, sem_cgpa, percentage 
                FROM marksheets WHERE student_id = ? ORDER BY semester
            """, (student_id,))
            rows = c.fetchall()
            for row in rows:
                marksheet_data["semesters"].append({
                    "semester": row[0],
                    "gpa": row[1],
                    "cgpa": row[2],
                    "percentage": row[3]
                })
            if rows:
                # Get latest CGPA
                latest_cgpa = [r[2] for r in rows if r[2] is not None]
                if latest_cgpa:
                    marksheet_data["cumulative_cgpa"] = latest_cgpa[-1]
        conn.close()
    
    # Get quiz dashboard
    quiz_data = {"last_score": None, "average_score": None, "quiz_count": 0}
    quiz_student_id = get_or_create_quiz_student(user_id, sap_no, full_name)
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute("SELECT score, total FROM quiz_results WHERE student_id = ? ORDER BY taken_at DESC", (quiz_student_id,))
    results = c.fetchall()
    conn.close()
    if results:
        quiz_data["quiz_count"] = len(results)
        last_score, last_total = results[0]
        quiz_data["last_score"] = round((last_score/last_total)*100, 2) if last_total > 0 else 0
        avg = sum([r[0]/r[1]*100 for r in results if r[1] > 0]) / len(results)
        quiz_data["average_score"] = round(avg, 2)
    
    # Resume analysis placeholder (could be stored in user_files or separate table)
    resume_data = {"status": "not_uploaded", "last_score": None}
    
    return {
        "user": {
            "id": user_id,
            "full_name": full_name,
            "email": current_user["email"],
            "sap_no": sap_no
        },
        "marksheets": marksheet_data,
        "quiz": quiz_data,
        "resume": resume_data
    }

# ============= Upload Marksheet (Student) =============
@router.post("/upload-marksheet/")
async def upload_marksheet_student(
    file: UploadFile = File(...),
    semester: int = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Student uploads their own marksheet. SAP number is auto-filled from auth.
    """
    sap_no = current_user.get("sap_no")
    full_name = current_user.get("full_name") or "Student"
    
    if not sap_no:
        return JSONResponse({"error": "SAP number not found in profile. Please update your profile."}, status_code=400)
    
    # Use marksheet_router logic
    from .marksheet_router import parse_marksheet_pdf_bytes, get_or_create_student, insert_marksheet
    
    content = await file.read()
    parsed = parse_marksheet_pdf_bytes(content)
    
    # Override with user's SAP
    parsed["sap_no"] = sap_no
    parsed["student_name"] = full_name
    
    sem = semester or parsed.get("semester") or 0
    acad = parsed.get("academic_year") or ""
    
    conn = sqlite3.connect("marksheets.db")
    student_id = get_or_create_student(conn, sap_no, full_name)
    ms_id = insert_marksheet(conn, student_id, sem, acad, file.filename, parsed)
    conn.close()
    
    # Record in user_files
    conn = sqlite3.connect("auth.db")
    c = conn.cursor()
    c.execute("INSERT INTO user_files (user_id, file_type, filename) VALUES (?, 'marksheet', ?)", 
              (current_user["id"], file.filename))
    conn.commit()
    conn.close()
    
    return JSONResponse({
        "status": "ok",
        "student_id": student_id,
        "marksheet_id": ms_id,
        "parsed": parsed
    })

# ============= Upload Resume (Student) =============
@router.post("/upload-resume/")
async def upload_resume_student(
    resume: UploadFile = File(...),
    job_description_text: str = Form(""),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Student uploads resume and gets analysis.
    """
    from .resume_router import extract_text_from_pdf_bytes, compute_match_score_from_resume_and_jd, generate_roadmap, extract_email, extract_name, extract_skill_candidates
    
    try:
        resume_bytes = await resume.read()
        resume_text = extract_text_from_pdf_bytes(resume_bytes)
    except Exception as e:
        return JSONResponse({"error": "Failed to read resume file", "detail": str(e)}, status_code=400)
    
    jd_text = job_description_text or "General software engineering position requiring programming skills, problem solving, and communication."
    
    email = extract_email(resume_text)
    name = extract_name(resume_text)
    candidate_skills = extract_skill_candidates(resume_text)
    
    scoring = compute_match_score_from_resume_and_jd(resume_text, jd_text)
    roadmap = generate_roadmap(scoring["missing_skills"], jd_text, scoring["match_score"])
    
    # Record in user_files
    conn = sqlite3.connect("auth.db")
    c = conn.cursor()
    c.execute("INSERT INTO user_files (user_id, file_type, filename) VALUES (?, 'resume', ?)", 
              (current_user["id"], resume.filename))
    conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "parsed": {
            "name": name,
            "email": email,
            "skills_extracted": candidate_skills,
            "experience_months": scoring["experience_months"]
        },
        "match": {
            "score": scoring["match_score"],
            "semantic_similarity": scoring["semantic_similarity"],
            "skill_overlap": scoring["skill_overlap"],
            "matched_skills": scoring["matched_skills"],
            "missing_skills": scoring["missing_skills"],
            "confidence": scoring["confidence"]
        },
        "roadmap": roadmap
    }

# ============= Generate Quiz (Student) =============
@router.get("/quiz/generate")
async def generate_quiz_student(
    num_questions: int = 12,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate adaptive quiz for current student.
    """
    sap_no = current_user.get("sap_no") or ""
    full_name = current_user.get("full_name") or "Student"
    user_id = current_user["id"]
    
    quiz_student_id = get_or_create_quiz_student(user_id, sap_no, full_name)
    
    # Use quiz logic
    from .quiz_router import generate_quiz
    result = generate_quiz(quiz_student_id, num_questions)
    return result

# ============= Submit Quiz (Student) =============
@router.post("/quiz/submit")
async def submit_quiz_student(
    answers: list,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Submit quiz answers for current student.
    """
    sap_no = current_user.get("sap_no") or ""
    full_name = current_user.get("full_name") or "Student"
    user_id = current_user["id"]
    
    quiz_student_id = get_or_create_quiz_student(user_id, sap_no, full_name)
    
    # Use quiz submit logic
    from .quiz_router import db_conn, ensure_student_exists, TOPICS, DIFFICULTIES
    import json
    
    ensure_student_exists(quiz_student_id)
    qids = [ans["qid"] for ans in answers if "qid" in ans]
    
    if not qids:
        return JSONResponse({"error": "no qids provided"}, status_code=400)
    
    conn = db_conn()
    c = conn.cursor()
    placeholders = ",".join("?" for _ in qids)
    c.execute(f"SELECT id, topic, difficulty, correct_option FROM quiz_questions WHERE id IN ({placeholders})", tuple(qids))
    rows = c.fetchall()
    meta = {r[0]: {"topic": r[1], "difficulty": r[2], "correct": r[3]} for r in rows}
    
    total = 0
    correct = 0
    per_topic = {t: {d: {"correct":0, "total":0} for d in DIFFICULTIES} for t in TOPICS}
    
    for ans in answers:
        qid = ans.get("qid")
        choice = (ans.get("answer") or "").lower()
        if qid not in meta:
            continue
        total += 1
        m = meta[qid]
        t = m["topic"]
        d = m["difficulty"] or "medium"
        per_topic[t][d]["total"] += 1
        if choice and choice.lower() == (m["correct"] or "").lower():
            correct += 1
            per_topic[t][d]["correct"] += 1
    
    scores_json = json.dumps(per_topic)
    c.execute("INSERT INTO quiz_results (student_id, score, total, scores_json) VALUES (?, ?, ?, ?)",
              (quiz_student_id, correct, total, scores_json))
    conn.commit()
    conn.close()
    
    percent = round((correct/total)*100, 2) if total > 0 else 0.0
    
    return {
        "status": "ok",
        "student_id": quiz_student_id,
        "score": correct,
        "total": total,
        "percent": percent,
        "per_topic": per_topic
    }

# ============= Quiz Dashboard (Student) =============
@router.get("/quiz/dashboard")
async def quiz_dashboard_student(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get quiz performance dashboard for current student.
    """
    sap_no = current_user.get("sap_no") or ""
    full_name = current_user.get("full_name") or "Student"
    user_id = current_user["id"]
    
    quiz_student_id = get_or_create_quiz_student(user_id, sap_no, full_name)
    
    from .quiz_router import quiz_dashboard
    result = quiz_dashboard(quiz_student_id)
    return result

