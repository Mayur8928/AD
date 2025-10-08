# backend/admin_router.py
# Admin-specific protected endpoints
import sqlite3
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from .auth import require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

# ============= List All Users =============
@router.get("/users/")
async def list_users(
    page: int = 1,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    List all users (students) with pagination.
    Admin-only endpoint.
    """
    offset = (page - 1) * limit
    
    conn = sqlite3.connect("auth.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total = c.fetchone()[0]
    
    c.execute("""
        SELECT id, email, full_name, sap_no, created_at 
        FROM users 
        WHERE role = 'student'
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    rows = c.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            "id": row[0],
            "email": row[1],
            "full_name": row[2],
            "sap_no": row[3],
            "created_at": row[4]
        })
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": users
    }

# ============= Get User Details =============
@router.get("/user/{user_id}")
async def get_user_details(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Get full details of a user including:
    - User info
    - Uploaded files
    - Marksheet data
    - Quiz history
    Admin-only endpoint.
    """
    # Get user info
    conn = sqlite3.connect("auth.db")
    c = conn.cursor()
    c.execute("SELECT id, email, full_name, sap_no, role, created_at FROM users WHERE id = ?", (user_id,))
    user_row = c.fetchone()
    if not user_row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    user_info = {
        "id": user_row[0],
        "email": user_row[1],
        "full_name": user_row[2],
        "sap_no": user_row[3],
        "role": user_row[4],
        "created_at": user_row[5]
    }
    
    # Get uploaded files
    c.execute("SELECT id, file_type, filename, uploaded_at FROM user_files WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,))
    files = [{"id": r[0], "file_type": r[1], "filename": r[2], "uploaded_at": r[3]} for r in c.fetchall()]
    conn.close()
    
    sap_no = user_info["sap_no"]
    
    # Get marksheet data
    marksheets = []
    if sap_no:
        conn = sqlite3.connect("marksheets.db")
        c = conn.cursor()
        c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
        student_row = c.fetchone()
        if student_row:
            student_id = student_row[0]
            c.execute("""
                SELECT semester, academic_year, sem_gpa, sem_cgpa, percentage, uploaded_filename
                FROM marksheets WHERE student_id = ? ORDER BY semester
            """, (student_id,))
            rows = c.fetchall()
            for row in rows:
                marksheets.append({
                    "semester": row[0],
                    "academic_year": row[1],
                    "gpa": row[2],
                    "cgpa": row[3],
                    "percentage": row[4],
                    "filename": row[5]
                })
        conn.close()
    
    # Get quiz history
    quiz_history = []
    if sap_no:
        conn = sqlite3.connect("quiz.db")
        c = conn.cursor()
        c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
        student_row = c.fetchone()
        if student_row:
            quiz_student_id = student_row[0]
            c.execute("""
                SELECT score, total, taken_at
                FROM quiz_results WHERE student_id = ? ORDER BY taken_at DESC LIMIT 20
            """, (quiz_student_id,))
            rows = c.fetchall()
            for row in rows:
                score, total, taken_at = row
                percent = round((score/total)*100, 2) if total > 0 else 0
                quiz_history.append({
                    "score": score,
                    "total": total,
                    "percent": percent,
                    "taken_at": taken_at
                })
        conn.close()
    
    return {
        "user": user_info,
        "files": files,
        "marksheets": marksheets,
        "quiz_history": quiz_history
    }

# ============= Delete User =============
@router.delete("/user/{user_id}")
async def delete_user(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Delete a user and their related data.
    Admin-only endpoint.
    Warning: This cascades to user_files, and optionally quiz results.
    """
    # Get user info first
    conn = sqlite3.connect("auth.db")
    c = conn.cursor()
    c.execute("SELECT id, sap_no, role FROM users WHERE id = ?", (user_id,))
    user_row = c.fetchone()
    if not user_row:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    if user_row[2] == "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot delete admin users")
    
    sap_no = user_row[1]
    
    # Delete from auth.db (cascade will delete user_files)
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    # Optionally delete from quiz.db
    if sap_no:
        conn = sqlite3.connect("quiz.db")
        c = conn.cursor()
        c.execute("DELETE FROM quiz_results WHERE student_id IN (SELECT id FROM students WHERE sap_no = ?)", (sap_no,))
        c.execute("DELETE FROM students WHERE sap_no = ?", (sap_no,))
        conn.commit()
        conn.close()
    
    return {"status": "ok", "message": f"User {user_id} deleted successfully"}

# ============= Reprocess Marksheet =============
@router.post("/user/{user_id}/reprocess-marksheet")
async def reprocess_marksheet(
    user_id: int,
    semester: int,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Trigger reprocessing of a marksheet for a specific semester.
    Admin-only endpoint.
    Note: This is a placeholder - actual file re-upload would be needed.
    """
    # Get user SAP
    conn = sqlite3.connect("auth.db")
    c = conn.cursor()
    c.execute("SELECT sap_no FROM users WHERE id = ?", (user_id,))
    user_row = c.fetchone()
    conn.close()
    
    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")
    
    sap_no = user_row[0]
    if not sap_no:
        raise HTTPException(status_code=400, detail="User has no SAP number")
    
    # Delete existing marksheet for this semester
    conn = sqlite3.connect("marksheets.db")
    c = conn.cursor()
    c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
    student_row = c.fetchone()
    if student_row:
        student_id = student_row[0]
        c.execute("DELETE FROM marksheets WHERE student_id = ? AND semester = ?", (student_id, semester))
        conn.commit()
    conn.close()
    
    return {
        "status": "ok",
        "message": f"Marksheet for semester {semester} deleted. User can re-upload."
    }

# ============= Update Settings (Admin) =============
@router.post("/settings/update")
async def update_quiz_settings(
    key: str,
    value: str,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Update quiz app settings (admin only).
    """
    from .quiz_router import set_setting
    
    allowed_keys = {"promote_threshold", "demote_threshold", "weak_topic_threshold", 
                   "weak_share_fraction", "lookback_quizzes", "weak_lookback"}
    
    if key not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"Invalid key. Allowed: {', '.join(sorted(allowed_keys))}")
    
    set_setting(key, value)
    return {"status": "ok", "key": key, "value": value}

@router.get("/settings/")
async def get_quiz_settings(current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Get current quiz settings (admin only).
    """
    from .quiz_router import list_settings
    return list_settings()

# ============= Admin Stats Dashboard =============
@router.get("/stats/")
async def admin_stats(current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Get overall statistics for admin dashboard.
    """
    # Count total students
    conn = sqlite3.connect("auth.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
    total_students = c.fetchone()[0]
    conn.close()
    
    # Count total marksheets uploaded
    conn = sqlite3.connect("marksheets.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM marksheets")
    total_marksheets = c.fetchone()[0]
    conn.close()
    
    # Count total quizzes taken
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM quiz_results")
    total_quizzes = c.fetchone()[0]
    c.execute("SELECT AVG(score * 100.0 / total) FROM quiz_results WHERE total > 0")
    avg_quiz_score = c.fetchone()[0]
    conn.close()
    
    # Count total files uploaded
    conn = sqlite3.connect("auth.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM user_files")
    total_files = c.fetchone()[0]
    conn.close()
    
    return {
        "total_students": total_students,
        "total_marksheets": total_marksheets,
        "total_quizzes": total_quizzes,
        "average_quiz_score": round(avg_quiz_score, 2) if avg_quiz_score else 0,
        "total_files_uploaded": total_files
    }

