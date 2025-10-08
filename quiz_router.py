# backend/quiz_router.py
# Refactored from quiz.py to work as a router
import sqlite3
import json
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import JSONResponse

DB_PATH = "quiz.db"
router = APIRouter(prefix="/quiz", tags=["Quiz"])

TOPICS = ["python", "sql", "logical", "quant", "language", "statistics"]
DIFFICULTIES = ["easy", "medium", "hard"]

# ----------------- DB init + settings table -----------------
def init_db():
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
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL DEFAULT 'medium',
        question TEXT NOT NULL,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_option TEXT NOT NULL
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        score INTEGER,
        total INTEGER,
        scores_json TEXT,
        taken_at TEXT DEFAULT (DATETIME('now')),
        FOREIGN KEY(student_id) REFERENCES students(id)
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    defaults = {
        "promote_threshold": "0.7",
        "demote_threshold": "0.4",
        "weak_topic_threshold": "0.5",
        "weak_share_fraction": "0.30",
        "lookback_quizzes": "6",
        "weak_lookback": "3"
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()

init_db()

# ----------------- Settings helpers -----------------
def db_conn():
    return sqlite3.connect(DB_PATH)

def get_setting(key: str, fallback: Optional[Any] = None) -> Optional[str]:
    conn = db_conn(); c = conn.cursor()
    c.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    r = c.fetchone(); conn.close()
    if r:
        return r[0]
    return fallback

def set_setting(key: str, value: str):
    conn = db_conn(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit(); conn.close()

def get_setting_float(key: str, fallback: float) -> float:
    v = get_setting(key, None)
    try:
        return float(v) if v is not None else fallback
    except:
        return fallback

def get_setting_int(key: str, fallback: int) -> int:
    v = get_setting(key, None)
    try:
        return int(v) if v is not None else fallback
    except:
        return fallback

# ----------------- Utilities -----------------
def ensure_student_exists(student_id: int):
    conn = db_conn(); c = conn.cursor()
    c.execute("SELECT id FROM students WHERE id = ?", (student_id,))
    r = c.fetchone(); conn.close()
    if not r:
        raise HTTPException(status_code=404, detail="student not found")

def get_student_by_sap_local(sap: str) -> Optional[Dict[str,Any]]:
    conn = db_conn(); c = conn.cursor()
    c.execute("SELECT id, student_name, sap_no FROM students WHERE sap_no = ?", (sap,))
    r = c.fetchone(); conn.close()
    if not r:
        return None
    return {"id": r[0], "student_name": r[1], "sap_no": r[2]}

# ----------------- Seeding questions -----------------
@router.post("/seed-sample-questions/")
def seed_sample_questions():
    sample = [
        ("python","easy","What is the output of len([1,2,3])?","2","3","1","4","b"),
        ("python","medium","What does list.append(x) do?","Adds x to start","Adds x to end","Removes x","Sorts list","b"),
        ("python","hard","What is a generator in Python?","A list","A lazy iterable","A dict subtype","A function decorator","b"),
        ("sql","easy","Which clause filters rows?","GROUP BY","WHERE","HAVING","ORDER BY","b"),
        ("sql","medium","Which statement removes all rows but keeps table structure?","DROP","DELETE","TRUNCATE","ALTER","b"),
        ("logical","easy","Sequence: 2,4,6,8,?","10","9","11","12","a"),
        ("quant","easy","What is 10% of 50?","5","10","15","20","a"),
        ("language","easy","Choose the correct sentence:","She go home.","She goes home.","She going home.","She gone home.","b"),
        ("statistics","easy","Mean of [1,2,3] is?","1","2","3","4","b"),
    ]
    conn = db_conn(); c = conn.cursor()
    for topic, diff, q, a, b, cc, d, correct in sample:
        c.execute("""
        INSERT INTO quiz_questions (topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (topic, diff, q, a, b, cc, d, correct))
    conn.commit(); conn.close()
    return {"status":"ok", "inserted": len(sample)}

# ----------------- Question pool -----------------
def get_pool(topic: str, difficulty: Optional[str]=None) -> List[Dict[str,Any]]:
    conn = db_conn(); c = conn.cursor()
    if difficulty:
        c.execute("SELECT id, question, option_a, option_b, option_c, option_d FROM quiz_questions WHERE topic = ? AND difficulty = ?", (topic, difficulty))
    else:
        c.execute("SELECT id, question, option_a, option_b, option_c, option_d FROM quiz_questions WHERE topic = ?", (topic,))
    rows = c.fetchall(); conn.close()
    pool = []
    for r in rows:
        pool.append({"id": r[0], "question": r[1], "options": {"a": r[2], "b": r[3], "c": r[4], "d": r[5]}})
    return pool

# ----------------- Difficulty logic -----------------
def student_topic_difficulty_profile(student_id: int, lookback: int = 6) -> Dict[str, Dict[str, Optional[float]]]:
    conn = db_conn(); c = conn.cursor()
    c.execute("SELECT scores_json FROM quiz_results WHERE student_id = ? ORDER BY taken_at DESC LIMIT ?", (student_id, lookback))
    rows = c.fetchall(); conn.close()
    accum = {t: {d: {"correct":0, "total":0} for d in DIFFICULTIES} for t in TOPICS}
    for r in rows:
        sj = json.loads(r[0])
        for topic in TOPICS:
            topic_obj = sj.get(topic, {})
            for diff in DIFFICULTIES:
                v = topic_obj.get(diff)
                if isinstance(v, dict):
                    accum[topic][diff]["correct"] += v.get("correct", 0)
                    accum[topic][diff]["total"] += v.get("total", 0)
    result = {}
    for topic in TOPICS:
        result[topic] = {}
        for diff in DIFFICULTIES:
            tot = accum[topic][diff]["total"]
            if tot > 0:
                result[topic][diff] = round(accum[topic][diff]["correct"] / tot, 3)
            else:
                result[topic][diff] = None
    return result

def decide_difficulty_for_topic(student_id: int, topic: str, lookback: int = None) -> str:
    if lookback is None:
        lookback = get_setting_int("lookback_quizzes", 6)
    profile = student_topic_difficulty_profile(student_id, lookback=lookback)
    topic_profile = profile.get(topic, {})
    if all(topic_profile.get(d) is None for d in DIFFICULTIES):
        return "medium"
    med_rate = topic_profile.get("medium")
    easy_rate = topic_profile.get("easy")
    hard_rate = topic_profile.get("hard")
    baseline = None
    if med_rate is not None:
        baseline = ("medium", med_rate)
    elif easy_rate is not None:
        baseline = ("easy", easy_rate)
    elif hard_rate is not None:
        baseline = ("hard", hard_rate)
    else:
        return "medium"
    cur_diff, cur_rate = baseline
    promote_threshold = get_setting_float("promote_threshold", 0.7)
    demote_threshold = get_setting_float("demote_threshold", 0.4)
    if cur_rate is not None and cur_rate >= promote_threshold:
        if cur_diff == "easy": return "medium"
        elif cur_diff == "medium": return "hard"
        else: return "hard"
    if cur_rate is not None and cur_rate <= demote_threshold:
        if cur_diff == "hard": return "medium"
        elif cur_diff == "medium": return "easy"
        else: return "easy"
    return cur_diff or "medium"

# ----------------- Generate adaptive quiz -----------------
@router.get("/generate-quiz/{student_id}")
def generate_quiz(student_id: int, num_questions: int = 12, lookback_override: Optional[int]=None, weak_lookback_override: Optional[int]=None):
    ensure_student_exists(student_id)
    weak_lookback = weak_lookback_override if weak_lookback_override is not None else get_setting_int("weak_lookback", 3)
    weak_topic_threshold = get_setting_float("weak_topic_threshold", 0.5)
    weak_share_fraction = get_setting_float("weak_share_fraction", 0.30)

    conn = db_conn(); c = conn.cursor()
    c.execute("SELECT scores_json FROM quiz_results WHERE student_id = ? ORDER BY taken_at DESC LIMIT ?", (student_id, weak_lookback))
    rows = c.fetchall(); conn.close()
    per_topic_acc = {t: {"correct":0, "total":0} for t in TOPICS}
    for r in rows:
        sj = json.loads(r[0])
        for t in TOPICS:
            tdata = sj.get(t, {})
            for diff in DIFFICULTIES:
                v = tdata.get(diff)
                if isinstance(v, dict):
                    per_topic_acc[t]["correct"] += v.get("correct",0)
                    per_topic_acc[t]["total"] += v.get("total",0)
    weak = []
    for t in TOPICS:
        tot = per_topic_acc[t]["total"]
        if tot > 0:
            acc = per_topic_acc[t]["correct"]/tot
            if acc < weak_topic_threshold:
                weak.append(t)

    lookback_for_difficulty = lookback_override if lookback_override is not None else get_setting_int("lookback_quizzes", 6)
    target_difficulty = {t: decide_difficulty_for_topic(student_id, t, lookback=lookback_for_difficulty) for t in TOPICS}

    questions = []
    if weak:
        weak_share = max(1, int(num_questions * weak_share_fraction))
        per_weak = max(1, weak_share // len(weak))
        for t in weak:
            diff = target_difficulty.get(t, "medium")
            pool = get_pool(t, diff)
            random.shuffle(pool)
            chosen = pool[:per_weak]
            for q in chosen:
                q2 = q.copy(); q2["topic"]=t; q2["difficulty"]=diff
                questions.append(q2)

    remaining = num_questions - len(questions)
    per_topic = max(1, remaining // len(TOPICS))
    for t in TOPICS:
        if len(questions) >= num_questions:
            break
        diff = target_difficulty.get(t, "medium")
        pool = get_pool(t, diff)
        if len(pool) < per_topic:
            pool_any = get_pool(t, None)
            pool = pool_any
        random.shuffle(pool)
        take = min(per_topic, num_questions - len(questions), len(pool))
        chosen = pool[:take]
        for q in chosen:
            q2 = q.copy(); q2["topic"]=t; q2["difficulty"]=diff
            questions.append(q2)

    if len(questions) < num_questions:
        all_pool = []
        for t in TOPICS:
            all_pool.extend(get_pool(t, None))
        existing_ids = {q["id"] for q in questions}
        leftover = [q for q in all_pool if q["id"] not in existing_ids]
        if leftover:
            need = min(num_questions - len(questions), len(leftover))
            chosen = random.sample(leftover, need)
            for q in chosen:
                q2 = q.copy(); q2["topic"] = None; q2["difficulty"] = None
                questions.append(q2)

    random.shuffle(questions)
    payload = []
    for q in questions:
        payload.append({"qid": q["id"], "topic": q.get("topic"), "difficulty": q.get("difficulty"), "question": q["question"], "options": q["options"]})
    return {"student_id": student_id, "questions": payload, "count": len(payload), "target_difficulty": target_difficulty}

# ----------------- Submit quiz -----------------
@router.post("/submit-quiz/")
async def submit_quiz(request: Request):
    body = await request.json()
    student_id = body.get("student_id")
    answers = body.get("answers", [])
    if not student_id or not isinstance(answers, list):
        raise HTTPException(status_code=400, detail="student_id and answers required")
    ensure_student_exists(student_id)
    qids = [ans["qid"] for ans in answers if "qid" in ans]
    if not qids:
        raise HTTPException(status_code=400, detail="no qids provided")
    conn = db_conn(); c = conn.cursor()
    placeholders = ",".join("?" for _ in qids)
    c.execute(f"SELECT id, topic, difficulty, correct_option FROM quiz_questions WHERE id IN ({placeholders})", tuple(qids))
    rows = c.fetchall()
    meta = {r[0]: {"topic": r[1], "difficulty": r[2], "correct": r[3]} for r in rows}
    total = 0; correct = 0
    per_topic = {t: {d: {"correct":0, "total":0} for d in DIFFICULTIES} for t in TOPICS}
    for ans in answers:
        qid = ans.get("qid")
        choice = (ans.get("answer") or "").lower()
        if qid not in meta:
            continue
        total += 1
        m = meta[qid]
        t = m["topic"]; d = m["difficulty"] or "medium"
        per_topic[t][d]["total"] += 1
        if choice and choice.lower() == (m["correct"] or "").lower():
            correct += 1
            per_topic[t][d]["correct"] += 1
    scores_json = json.dumps(per_topic)
    c.execute("INSERT INTO quiz_results (student_id, score, total, scores_json) VALUES (?, ?, ?, ?)",
              (student_id, correct, total, scores_json))
    conn.commit(); conn.close()
    percent = round((correct/total)*100,2) if total>0 else 0.0
    return {"status":"ok", "student_id": student_id, "score": correct, "total": total, "percent": percent, "per_topic": per_topic}

# ----------------- Dashboard -----------------
@router.get("/quiz-dashboard/{student_id}")
def quiz_dashboard(student_id: int, history_count: int = 20):
    ensure_student_exists(student_id)
    conn = db_conn(); c = conn.cursor()
    c.execute("SELECT score, total, scores_json, taken_at FROM quiz_results WHERE student_id = ? ORDER BY taken_at ASC", (student_id,))
    rows = c.fetchall(); conn.close()
    if not rows:
        return {"student_id": student_id, "last_score": None, "average_score": None, "time_series": [], "topic_summary": {t: None for t in TOPICS}, "raw_results": []}
    time_series = []; per_topic_acc = {t: {"correct":0, "total":0} for t in TOPICS}
    percents = []; raw_results = []
    for r in rows:
        score, total, scores_json, taken_at = r
        percent = round((score/total)*100,2) if total>0 else None
        percents.append(percent)
        time_series.append({"taken_at": taken_at, "percent": percent})
        sj = json.loads(scores_json)
        for t in TOPICS:
            for diff in DIFFICULTIES:
                v = sj.get(t, {}).get(diff)
                if isinstance(v, dict):
                    per_topic_acc[t]["correct"] += v.get("correct",0)
                    per_topic_acc[t]["total"] += v.get("total",0)
        raw_results.append({"score":score,"total":total,"percent":percent,"scores_json":sj,"taken_at":taken_at})
    last_score = raw_results[-1]["percent"]
    average_score = round(sum([p for p in percents if p is not None]) / len([p for p in percents if p is not None]),2)
    topic_summary = {}
    for t in TOPICS:
        tot = per_topic_acc[t]["total"]
        topic_summary[t] = round((per_topic_acc[t]["correct"]/tot)*100,2) if tot>0 else None
    return {"student_id": student_id, "last_score": last_score, "average_score": average_score, "time_series": time_series, "topic_summary": topic_summary, "raw_results": raw_results}

# ----------------- Student topic profile -----------------
@router.get("/student-topic-profile/{student_id}")
def student_topic_profile(student_id: int, lookback: int = None):
    ensure_student_exists(student_id)
    if lookback is None:
        lookback = get_setting_int("lookback_quizzes", 6)
    profile = student_topic_difficulty_profile(student_id, lookback=lookback)
    suggested = {t: decide_difficulty_for_topic(student_id, t, lookback=lookback) for t in TOPICS}
    return {"student_id": student_id, "profile": profile, "suggested_difficulty": suggested}

# ----------------- Settings endpoints -----------------
@router.get("/settings/")
def list_settings():
    conn = db_conn(); c = conn.cursor()
    c.execute("SELECT key, value FROM app_settings")
    rows = c.fetchall(); conn.close()
    return {r[0]: r[1] for r in rows}

@router.post("/settings/")
def update_setting(key: str = Form(...), value: str = Form(...)):
    allowed_keys = {"promote_threshold","demote_threshold","weak_topic_threshold","weak_share_fraction","lookback_quizzes","weak_lookback"}
    if key not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"allowed keys: {', '.join(sorted(allowed_keys))}")
    set_setting(key, value)
    return {"status":"ok", "key": key, "value": value}

# ----------------- Utility endpoints -----------------
@router.get("/questions/")
def list_questions():
    conn = db_conn(); c = conn.cursor()
    c.execute("SELECT id, topic, difficulty, question, option_a, option_b, option_c, option_d FROM quiz_questions ORDER BY topic")
    rows = c.fetchall(); conn.close()
    res = []
    for r in rows:
        res.append({"id": r[0], "topic": r[1], "difficulty": r[2], "question": r[3], "options": {"a": r[4], "b": r[5], "c": r[6], "d": r[7]}})
    return res

@router.post("/add-question/")
def add_question(topic: str = Form(...), difficulty: str = Form("medium"), question: str = Form(...),
                 option_a: str = Form(""), option_b: str = Form(""), option_c: str = Form(""), option_d: str = Form(""),
                 correct_option: str = Form(...)):
    if topic not in TOPICS:
        raise HTTPException(status_code=400, detail="invalid topic")
    if difficulty not in DIFFICULTIES:
        raise HTTPException(status_code=400, detail="invalid difficulty")
    conn = db_conn(); c = conn.cursor()
    c.execute("INSERT INTO quiz_questions (topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option))
    conn.commit(); conn.close()
    return {"status":"ok"}

@router.post("/create-student/")
def create_student(student_name: str = Form(...), sap_no: str = Form(...)):
    conn = db_conn(); c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO students (student_name, sap_no) VALUES (?, ?)", (student_name, sap_no))
    conn.commit()
    c.execute("SELECT id FROM students WHERE sap_no = ?", (sap_no,))
    r = c.fetchone(); conn.close()
    return {"status":"ok", "student_id": r[0]}

@router.get("/student-by-sap/{sap}")
def get_student_by_sap(sap: str):
    s = get_student_by_sap_local(sap)
    if not s:
        raise HTTPException(status_code=404, detail="not found")
    return s

