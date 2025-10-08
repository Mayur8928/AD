# backend/resume_router.py
# Refactored from readinessscore.py to work as a router
import os
import re
import io
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

import pdfplumber
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import process, fuzz
import dateparser
from dateutil.relativedelta import relativedelta

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY and GEMINI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter(prefix="/resume", tags=["Resume Analyzer"])

# Embedding model
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
embed_model = SentenceTransformer(EMBED_MODEL_NAME)

# Canonical skill bank
ROLE_SKILLS = {
    "data_scientist": ["python", "sql", "statistics", "machine learning", "pandas", "numpy", "scikit-learn", "data visualization", "tableau", "matplotlib", "seaborn"],
    "software_developer": ["java", "python", "c++", "data structures", "algorithms", "git", "rest api", "docker", "ci/cd", "system design"],
    "ui_ux_designer": ["figma", "adobe xd", "user research", "wireframing", "prototyping", "usability testing", "interaction design"],
    "marketing_analyst": ["excel", "sql", "google analytics", "data visualization", "tableau", "campaign analysis", "a/b testing"],
}
CANONICAL_SKILLS = sorted({s for skills in ROLE_SKILLS.values() for s in skills})

# Text extraction
def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception:
        text = ""

    if (len(text.strip()) < 50) and TESSERACT_AVAILABLE:
        ocr_text = ""
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for i, page in enumerate(pdf.pages):
                    try:
                        pil_image = page.to_image(resolution=150).original
                        page_ocr = pytesseract.image_to_string(pil_image)
                        ocr_text += page_ocr + "\n"
                    except Exception:
                        continue
        except Exception:
            ocr_text = ""
        if len(ocr_text.strip()) > 0:
            text = ocr_text
    return text or ""

EMAIL_RE = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
YEARS_RE = re.compile(r"(\d+)\s*(?:\+)?\s*(?:years|yrs|year)")

def extract_email(text: str) -> Optional[str]:
    m = EMAIL_RE.search(text)
    return m.group(1) if m else None

def extract_name(text: str) -> Optional[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None
    first = lines[0]
    if 2 <= len(first.split()) <= 4 and not any(c.isdigit() for c in first):
        return first
    email = extract_email(text)
    if email:
        username = email.split("@")[0].replace(".", " ").replace("_", " ").title()
        return username
    return None

SECTION_HEADERS = {
    "experience": [
        r"work experience", r"professional experience", r"experience", r"employment history",
        r"roles and responsibilities", r"work history", r"professional background", r"career summary",
        r"professional summary"
    ],
    "education": [
        r"education", r"academic qualification", r"academics", r"qualifications", r"educational"
    ],
    "skills": [
        r"skills", r"technical skills", r"key skills", r"core skills", r"skills & technologies"
    ],
    "projects": [
        r"projects", r"personal projects", r"academic projects", r"selected projects"
    ],
    "certifications": [
        r"certifications", r"certificates", r"training"
    ]
}

SECTION_REGEX = {k: re.compile(r"^\s*(?:" + "|".join(v) + r")\s*$", flags=re.I | re.M) for k, v in SECTION_HEADERS.items()}
YEARS_EXP_RE = re.compile(r"(\d+)\s*\+?\s*(?:years|yrs|year)\b", flags=re.I)
DATE_RANGE_PATTERNS = [
    re.compile(r'([A-Za-z]{3,9}\s*\d{4})\s*[–—-]\s*(Present|Current|[A-Za-z]{3,9}\s*\d{4}|\d{4})', flags=re.I),
    re.compile(r'(\d{4})\s*[–—-]\s*(Present|Current|\d{4})', flags=re.I),
    re.compile(r'([A-Za-z]{3,9}\s*\d{4})\s*(?:to|TO|To)\s*([A-Za-z]{3,9}\s*\d{4}|Present|Current|\d{4})', flags=re.I),
]

def split_sections(text: str) -> Dict[str, str]:
    lines = [ln.rstrip() for ln in text.splitlines()]
    n = len(lines)
    headings = []
    for i, ln in enumerate(lines):
        for sec, pattern in SECTION_REGEX.items():
            if pattern.match(ln.strip()):
                headings.append((i, sec))
                break

    if not headings:
        for i, ln in enumerate(lines):
            lower = ln.lower()
            for sec, keys in SECTION_HEADERS.items():
                if any(k in lower for k in keys):
                    headings.append((i, sec))
                    break

    headings.sort()
    sections = {"experience": "", "education": "", "skills": "", "projects": "", "certifications": "", "other": ""}

    if not headings:
        sections["other"] = "\n".join(lines)
        return sections

    for idx, (start_idx, sec) in enumerate(headings):
        end_idx = headings[idx + 1][0] if idx + 1 < len(headings) else n
        content = "\n".join(lines[start_idx + 1:end_idx]).strip()
        if sections.get(sec):
            sections[sec] += "\n" + content
        else:
            sections[sec] = content

    first_heading_idx = headings[0][0]
    if first_heading_idx > 0:
        intro = "\n".join(lines[:first_heading_idx]).strip()
        if intro:
            sections["other"] = intro

    return sections

def parse_date_fuzzy(s: str) -> Optional[datetime]:
    s = s.strip()
    if not s:
        return None
    if s.lower() in ('present', 'current'):
        return datetime.now()
    dt = dateparser.parse(s, settings={'PREFER_DAY_OF_MONTH': 'first'})
    if dt:
        return dt
    m = re.match(r'^\d{4}$', s)
    if m:
        return datetime(int(s), 1, 1)
    return None

def extract_experience_months_v3(text: str) -> Tuple[int, List[Tuple[str, str, bool, int]]]:
    text = text or ""
    sections = split_sections(text)
    exp_text = sections.get("experience", "").strip()
    if not exp_text:
        exp_text = sections.get("other", "") or sections.get("projects", "") or sections.get("certifications", "") or text

    date_ranges = []
    for pat in DATE_RANGE_PATTERNS:
        for m in pat.finditer(exp_text):
            a, b = m.group(1), m.group(2)
            match_pos = m.start()
            pre = exp_text[max(0, match_pos-150): match_pos + 50].lower()
            experience_keywords = ['intern', 'internship', 'engineer', 'analyst', 'developer', 'data', 'manager', 'consultant', 'associate', 'research', 'product', 'lead', 'worked', 'worked at', 'at ', 'handled', 'responsible']
            likely_experience = any(k in pre for k in experience_keywords)
            date_ranges.append((a.strip(), b.strip(), likely_experience, match_pos))

    total_months = 0
    used_ranges = 0
    for a_str, b_str, likely_exp, pos in date_ranges:
        start_dt = parse_date_fuzzy(a_str)
        end_dt = parse_date_fuzzy(b_str)
        if not start_dt or not end_dt:
            continue
        if end_dt < start_dt:
            continue
        rd = relativedelta(end_dt, start_dt)
        months = rd.years * 12 + rd.months
        if months == 0 and start_dt.year != end_dt.year:
            months = (end_dt.year - start_dt.year) * 12
        if months > 0:
            total_months += months
            used_ranges += 1

    if used_ranges == 0:
        for m in YEARS_EXP_RE.finditer(exp_text):
            start = max(0, m.start() - 80)
            snippet = exp_text[start:m.end()+80].lower()
            if 'experience' in snippet or any(k in snippet for k in ['worked', 'intern', 'experience']):
                try:
                    years = int(m.group(1))
                    return years * 12, date_ranges
                except:
                    pass

    if used_ranges == 0:
        lines = [ln.strip() for ln in exp_text.splitlines() if ln.strip()]
        heur_count = sum(1 for ln in lines if re.search(r'\b(intern|internship|worked|research|project|developer|engineer|analyst)\b', ln, flags=re.I))
        if heur_count:
            total_months = heur_count * 6

    if total_months > 600:
        total_months = 0

    return int(total_months), date_ranges

def extract_skill_candidates(text: str) -> List[str]:
    txt = (text or "").lower()
    found = set()
    for skill in CANONICAL_SKILLS:
        if skill.lower() in txt:
            found.add(skill)
    tokens = re.findall(r"[A-Za-z0-9\+\#\.\-]{2,}", txt)
    for t in set(tokens):
        if len(t) < 3:
            continue
        best = process.extractOne(t, CANONICAL_SKILLS, scorer=fuzz.partial_ratio)
        if best and best[1] >= 90:
            found.add(best[0])
    return sorted(found)

def extract_required_skills_from_jd(text: str) -> List[str]:
    txt = text or ""
    skills_found = []

    m = re.search(r"(?:skills|requirements|must have|we are looking for)[:\-]\s*([\s\S]{0,400})", txt, flags=re.IGNORECASE)
    if m:
        block = m.group(1)
        block = block.split("\n\n")[0]
        parts = re.split(r"[,\n;••\-]+", block)
        for p in parts:
            p = p.strip()
            if len(p) > 1:
                p = re.sub(r"\(.*?\)", "", p).strip()
                p = " ".join(p.split()[:4]).lower()
                skills_found.append(p)

    canon = extract_skill_candidates(txt)
    for s in canon:
        if s not in skills_found:
            skills_found.append(s)

    cleaned = []
    for s in skills_found:
        ss = s.lower().strip()
        if ss and ss not in cleaned:
            cleaned.append(ss)
    return cleaned

def embed_text(text: str):
    short = (text or "").strip()
    if len(short) > 30000:
        short = short[:30000]
    emb = embed_model.encode([short], show_progress_bar=False)
    return emb

def compute_match_score_from_resume_and_jd(resume_text: str, jd_text: str) -> Dict[str, Any]:
    candidate_skills = extract_skill_candidates(resume_text)
    required_skills = extract_required_skills_from_jd(jd_text)

    try:
        jd_emb = embed_text(jd_text if jd_text.strip() else " ".join(required_skills))
        resume_emb = embed_text(resume_text)
        sim = float(cosine_similarity(jd_emb, resume_emb)[0][0])
        sim = max(0.0, min(1.0, sim))
    except Exception:
        sim = 0.0

    matched = []
    missing = []
    for r in required_skills:
        best = process.extractOne(r, candidate_skills, scorer=fuzz.token_sort_ratio) if candidate_skills else None
        if best and best[1] >= 75:
            matched.append(r)
        else:
            if any(r in c.lower() or c.lower() in r for c in candidate_skills):
                matched.append(r)
            else:
                missing.append(r)
    overlap = (len(matched) / max(1, len(required_skills))) if required_skills else 0.0

    experience_months, date_ranges = extract_experience_months_v3(resume_text)
    experience_score = min(1.0, experience_months / 36.0)

    w_skill = 0.5
    w_semantic = 0.35
    w_exp = 0.15

    raw = w_skill * overlap + w_semantic * sim + w_exp * experience_score
    match_score = round(raw * 100, 2)

    confidence = round(0.4 * (len(candidate_skills) / max(1, len(required_skills) if required_skills else 1)) + 0.6 * min(1.0, experience_months / 12.0), 2)
    confidence = max(0.05, min(1.0, confidence))

    return {
        "match_score": match_score,
        "semantic_similarity": round(sim, 3),
        "skill_overlap": round(overlap, 3),
        "matched_skills": matched,
        "missing_skills": missing,
        "candidate_skills": candidate_skills,
        "required_skills": required_skills,
        "experience_months": experience_months,
        "experience_score": round(experience_score, 3),
        "confidence": confidence,
        "date_ranges": date_ranges
    }

def generate_roadmap(missing_skills: List[str], jd_text: str, score: float) -> str:
    if GEMINI_API_KEY and GEMINI_AVAILABLE:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""
You are an AI career coach. A student scored {score:.1f}/100 for matching their resume with this job description:
\"\"\"{jd_text[:1200]}\"\"\"
They are missing these skills: {', '.join(missing_skills) if missing_skills else 'none'}.
Provide a concise, practical 3-week roadmap (3 bullets per week), focused on hands-on practice the student can complete.
Return plain text.
"""
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            pass

    lines = []
    if missing_skills:
        lines.append(f"Week 1 — Focus on {missing_skills[0]}. Daily practice: 30-60 mins, 5 small problems, 1 mini-project sample.")
        if len(missing_skills) > 1:
            lines.append(f"Week 2 — Focus on {missing_skills[1]}. Build a short notebook demonstrating usage.")
        else:
            lines.append("Week 2 — Strengthen data structures and core algorithms relevant to the role.")
        lines.append("Week 3 — Mock interviews, refine resume bullets (use metrics), and do 2 timed coding problems daily.")
    else:
        lines = [
            "Week 1 — Review core technologies mentioned in the JD and complete 3 practice tasks.",
            "Week 2 — Build/polish a relevant mini project and add measurable achievements to your resume.",
            "Week 3 — Mock interviews and refine your elevator pitch and HR answers (STAR format)."
        ]
    return "\n".join([f"- {l}" for l in lines])

@router.post("/analyze/")
async def resume_check(
    resume: UploadFile = File(...),
    job_description_file: Optional[UploadFile] = File(None),
    job_description_text: str = Form("")
):
    """
    Upload resume (PDF) and JD (PDF or text). Returns parsed fields, match, missing skills, and a roadmap.
    """
    try:
        resume_bytes = await resume.read()
        resume_text = extract_text_from_pdf_bytes(resume_bytes)
    except Exception as e:
        return JSONResponse({"error": "Failed to read resume file", "detail": str(e)}, status_code=400)

    jd_text = ""
    if job_description_file:
        try:
            jd_bytes = await job_description_file.read()
            jd_text += extract_text_from_pdf_bytes(jd_bytes)
        except Exception:
            pass
    if job_description_text:
        jd_text += "\n" + job_description_text

    if not jd_text.strip():
        return JSONResponse({"error": "Please provide a job description (file or text)"}, status_code=400)

    email = extract_email(resume_text)
    name = extract_name(resume_text)
    candidate_skills = extract_skill_candidates(resume_text)

    scoring = compute_match_score_from_resume_and_jd(resume_text, jd_text)
    roadmap = generate_roadmap(scoring["missing_skills"], jd_text, scoring["match_score"])

    sections = split_sections(resume_text)
    exp_section_text = sections.get("experience", "") or sections.get("other", "")
    exp_section_text_trunc = exp_section_text[:2000]

    date_ranges_detected = scoring.get("date_ranges", [])

    response = {
        "parsed": {
            "name": name,
            "email": email,
            "skills_extracted": candidate_skills,
            "experience_months": scoring["experience_months"],
            "experience_section_text": exp_section_text_trunc
        },
        "job_description_excerpt": jd_text[:1200],
        "match": {
            "score": scoring["match_score"],
            "semantic_similarity": scoring["semantic_similarity"],
            "skill_overlap": scoring["skill_overlap"],
            "matched_skills": scoring["matched_skills"],
            "missing_skills": scoring["missing_skills"],
            "confidence": scoring["confidence"]
        },
        "roadmap": roadmap,
        "debug": {
            "date_ranges_detected": [
                {"start": a, "end": b, "likely_experience": likely, "pos": pos} for (a, b, likely, pos) in date_ranges_detected
            ]
        }
    }
    return JSONResponse(response)

@router.get("/health")
def health():
    return {
        "status": "ok",
        "embed_model": EMBED_MODEL_NAME,
        "tesseract_available": TESSERACT_AVAILABLE,
        "gemini_available": bool(GEMINI_API_KEY and GEMINI_AVAILABLE)
    }

