# backend/marksheet_router.py
# Refactored from marksheet_app.py to work as a router
import io
import re
import sqlite3
from typing import Dict, Any, Optional
from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse
import pdfplumber

DB_PATH = "marksheets.db"
router = APIRouter(prefix="/marksheet", tags=["Marksheets"])

# ---------- initialize DB ----------
def init_db_and_migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        sap_no TEXT UNIQUE
    );
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS marksheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        semester INTEGER,
        academic_year TEXT,
        uploaded_filename TEXT,
        sem_gpa REAL,
        sem_cgpa REAL,
        percentage REAL,
        total_obtained REAL,
        total_max REAL,
        raw_json TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    """)
    conn.commit()
    conn.close()

init_db_and_migrate()

def only_digits(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    d = re.sub(r"\D", "", s)
    return d if d else None

# ---------- PDF parsing ----------
def parse_marksheet_pdf_bytes(file_bytes: bytes) -> Dict[str, Any]:
    text_all = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text_all += "\n" + (page.extract_text() or "")

    header_text = text_all[:2000]

    # Name
    student_name = None
    mname = re.search(r"Name\s*[:\-]?\s*(.+?)(?:\s+SAP\b|\n|$)", header_text, flags=re.I)
    if mname:
        student_name = mname.group(1).strip()
    
    # SAP extraction
    sap_no = None
    msap = re.search(r"SAP\s*No\.?\s*[:\-]?\s*([0-9]+)", header_text, flags=re.I)
    if msap:
        sap_no = only_digits(msap.group(1))
    else:
        m = re.search(r"\b(\d{6,12})\b", header_text)
        if m:
            sap_no = only_digits(m.group(1))

    # Semester
    semester = None
    msem = re.search(r"Semester\s+([IVX]+|\d+)", header_text, flags=re.I)
    if msem:
        sem_raw = msem.group(1).strip()
        roman_map = {"I":1,"II":2,"III":3,"IV":4,"V":5,"VI":6,"VII":7,"VIII":8}
        semester = int(sem_raw) if sem_raw.isdigit() else roman_map.get(sem_raw.upper())

    # Academic Year
    academic_year = None
    macad = re.search(r"Academic Year[:\s]*([0-9]{4}\s*-\s*[0-9]{4}|[0-9]{4})", header_text, flags=re.I)
    if macad:
        academic_year = macad.group(1).strip()

    # GPA & CGPA
    sem_gpa_from_sheet = None
    sem_cgpa_from_sheet = None
    mgpa = re.search(r"GPA\s*[:\-]?\s*([0-9]+\.[0-9]+)", text_all, flags=re.I)
    mcgpa = re.search(r"CGPA\s*[:\-]?\s*([0-9]+\.[0-9]+)", text_all, flags=re.I)
    if mgpa:
        sem_gpa_from_sheet = float(mgpa.group(1))
    if mcgpa:
        sem_cgpa_from_sheet = float(mcgpa.group(1))

    # Subject rows & percentage
    total_obt = 0.0
    total_max = 0.0
    subjects = []
    for line in text_all.splitlines():
        if re.search(r"\b(O|A\+|A|B\+|B|C|P|F)\b", line):
            nums = re.findall(r"\d{1,3}", line)
            if len(nums) >= 2:
                obtained = float(nums[-2])
                max_marks = float(nums[-1])
                if max_marks > 0 and obtained <= max_marks:
                    total_obt += obtained
                    total_max += max_marks
                    subjects.append({"raw": line, "final_marks": obtained, "final_max": max_marks})

    percentage = round((total_obt / total_max) * 100, 2) if total_max > 0 else None

    return {
        "student_name": student_name,
        "sap_no": sap_no,
        "semester": semester,
        "academic_year": academic_year,
        "sem_gpa": sem_gpa_from_sheet,
        "sem_cgpa": sem_cgpa_from_sheet,
        "percentage": percentage,
        "total_obtained": total_obt,
        "total_max": total_max,
        "subjects": subjects
    }

# ---------- DB helpers ----------
def get_or_create_student(conn, sap_no: Optional[str], student_name: Optional[str]) -> int:
    c = conn.cursor()
    if sap_no:
        c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
        r = c.fetchone()
        if r:
            return r[0]
    if student_name:
        c.execute("SELECT id FROM students WHERE student_name = ?", (student_name,))
        r = c.fetchone()
        if r:
            return r[0]
    c.execute("INSERT INTO students (student_name, sap_no) VALUES (?, ?)", (student_name, sap_no))
    conn.commit()
    return c.lastrowid

def insert_marksheet(conn, student_id:int, semester:int, academic_year:str, filename:str, parsed:Dict[str,Any]):
    c = conn.cursor()
    # Remove old entry if same semester already exists
    c.execute("DELETE FROM marksheets WHERE student_id = ? AND semester = ?", (student_id, semester))
    # Insert new one
    c.execute("""
    INSERT INTO marksheets (student_id, semester, academic_year, uploaded_filename, 
        sem_gpa, sem_cgpa, percentage, total_obtained, total_max, raw_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_id, semester or 0, academic_year, filename,
          parsed.get("sem_gpa"), parsed.get("sem_cgpa"), parsed.get("percentage"),
          parsed.get("total_obtained"), parsed.get("total_max"), str(parsed)))
    conn.commit()
    return c.lastrowid

# ---------- API ----------
@router.post("/upload-marksheet/")
async def upload_marksheet(file: UploadFile = File(...), sap_no: str = Form(None), semester: int = Form(None)):
    """Upload and parse marksheet PDF"""
    content = await file.read()
    parsed = parse_marksheet_pdf_bytes(content)
    sap = sap_no or parsed.get("sap_no")
    name = parsed.get("student_name")
    sem = semester or parsed.get("semester") or 0
    acad = parsed.get("academic_year") or ""
    conn = sqlite3.connect(DB_PATH)
    student_id = get_or_create_student(conn, sap, name)
    ms_id = insert_marksheet(conn, student_id, sem, acad, file.filename, parsed)
    conn.close()
    return JSONResponse({"status": "ok", "student_id": student_id, "marksheet_id": ms_id, "parsed": parsed})

@router.get("/students/")
def list_students():
    """
    Aggregated table:
    sem1_gpa..sem8_gpa, cumulative_cgpa (latest semester's CGPA), overall_percentage.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, student_name, sap_no FROM students ORDER BY id asc")
    students = c.fetchall()
    out = []
    for sid, sname, ssap in students:
        c.execute("SELECT semester, sem_gpa, sem_cgpa, percentage, total_obtained, total_max FROM marksheets WHERE student_id = ?", (sid,))
        rows = c.fetchall()
        sem_map = {}
        total_obt = total_max = 0.0
        for semn, gpa, cgpa, perc, obt, mx in rows:
            sem_map[int(semn)] = {"gpa": gpa, "cgpa": cgpa, "percentage": perc}
            if obt and mx:
                total_obt += obt
                total_max += mx
        # cumulative_cgpa = CGPA of highest semester present
        cumulative_cgpa = None
        if sem_map:
            available_semesters = sorted([int(s) for s in sem_map.keys() if sem_map[s].get("cgpa") is not None])
            if available_semesters:
                highest_sem = available_semesters[-1]
                cumulative_cgpa = sem_map[highest_sem]["cgpa"]

        overall_percentage = round((total_obt/total_max)*100,2) if total_max>0 else None
        sem_cols = {}
        for s_i in range(1, 9):
            sem_cols[f"sem{s_i}_gpa"] = sem_map.get(s_i, {}).get("gpa")
        out.append({
            "student_id": sid,
            "student_name": sname,
            "sap_no": ssap,
            **sem_cols,
            "cumulative_cgpa": cumulative_cgpa,
            "overall_percentage": overall_percentage
        })
    conn.close()
    return JSONResponse(out)

@router.get("/student/{sap_no}")
def get_student_marksheets(sap_no: str):
    """Get all marksheets for a specific student by SAP number"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
    student = c.fetchone()
    if not student:
        conn.close()
        return JSONResponse({"error": "Student not found"}, status_code=404)
    
    student_id = student[0]
    c.execute("""
        SELECT semester, academic_year, sem_gpa, sem_cgpa, percentage, uploaded_filename 
        FROM marksheets WHERE student_id = ? ORDER BY semester
    """, (student_id,))
    rows = c.fetchall()
    conn.close()
    
    marksheets = []
    for row in rows:
        marksheets.append({
            "semester": row[0],
            "academic_year": row[1],
            "sem_gpa": row[2],
            "sem_cgpa": row[3],
            "percentage": row[4],
            "filename": row[5]
        })
    
    return JSONResponse({"sap_no": sap_no, "marksheets": marksheets})

