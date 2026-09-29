import io

import pdfplumber
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from db.session import get_db_connection
from services.reranker import rerank_and_justify
from sentence_transformers import SentenceTransformer

router = APIRouter()

# Lazy load model to prevent 2.3GB download on server startup if not immediately needed
_model = None
def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('BAAI/bge-m3')
    return _model

class AnalyzeRequest(BaseModel):
    text: str

MAX_UPLOAD_BYTES = 20 * 1024 * 1024   # 20 MB
MAX_EXTRACTED_CHARS = 20000          # keep the embedding cost bounded
CANDIDATE_LIMIT = 5


def run_analysis(text: str) -> dict:
    """Shared pipeline used by both /analyze and /analyze-file.

    embed -> pgvector cosine search -> LLM rerank -> response dict
    """
    text = (text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="No text to analyse.")

    model = get_model()
    query_embedding = model.encode(text, normalize_embeddings=True).tolist()

    conn = get_db_connection()
    cur = conn.cursor()

    # FIXED: ORDER BY cosine distance ASC (lower distance = higher similarity)
    cur.execute("""
        SELECT is_number, title, scope_text, status, latest_amendment, superseded_by, category,
               (scope_embedding <=> %s::vector) as distance
        FROM standards
        ORDER BY distance ASC
        LIMIT %s;
    """, (str(query_embedding), CANDIDATE_LIMIT))

    candidates = cur.fetchall()
    if not candidates:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="No standards found")

    llm_result = rerank_and_justify(text, candidates)
    selected_numbers = llm_result.get("selected_is_numbers", [])

    primary_recs = []
    allied_standards = {"test_methods": [], "terminology": [], "safety": [], "installation": []}
    certifications_info = []  # list so every applicable certification is kept

    for c in candidates:
        if c["is_number"] in selected_numbers:
            # Convert distance (0 to 2) to similarity (1 to -1), then to confidence
            similarity = 1 - c["distance"]
            confidence = "High" if similarity > 0.85 else "Medium" if similarity > 0.70 else "Low"

            # NOTE: no per-standard justification - the LLM returns one shared
            # rationale for the whole selection, returned once at the top level.
            primary_recs.append({
                "is_number": c["is_number"],
                "title": c["title"],
                "status": c["status"],
                "latest_amendment": c["latest_amendment"],
                "confidence": confidence
            })

            cur.execute("""
                SELECT s.is_number, s.title, sr.relation_type
                FROM standard_relations sr
                JOIN standards s ON sr.related_standard_id = s.id
                WHERE sr.standard_id = (SELECT id FROM standards WHERE is_number = %s)
            """, (c["is_number"],))
            for rel in cur.fetchall():
                if rel["relation_type"] in allied_standards:
                    allied_standards[rel["relation_type"]].append({"is_number": rel["is_number"], "title": rel["title"]})

            cur.execute("SELECT scheme_name, mandatory, notes FROM certifications WHERE category = %s OR is_number = %s", (c["category"], c["is_number"]))
            certs = cur.fetchall()
            for cert in certs:
                if cert["mandatory"] and cert["scheme_name"] not in [ci["scheme_name"] for ci in certifications_info]:
                    certifications_info.append({"scheme_name": cert["scheme_name"], "mandatory": True, "notes": cert["notes"]})

    # FIXED: a standard that is already a primary recommendation must not also be
    # listed as an allied standard, and the same allied standard must not repeat
    # when two primaries relate to it.
    selected_set = {rec["is_number"] for rec in primary_recs}
    for key, items in allied_standards.items():
        seen = set()
        unique = []
        for item in items:
            number = item["is_number"]
            if number in selected_set or number in seen:
                continue
            seen.add(number)
            unique.append(item)
        allied_standards[key] = unique

    cur.close()
    conn.close()

    return {
        "justification": llm_result.get("justification", ""),
        "primary_recommendations": primary_recs,
        "allied_standards": allied_standards,
        "certifications": certifications_info
    }


@router.post("/analyze")
def analyze_spec(request: AnalyzeRequest):
    return run_analysis(request.text)


@router.post("/analyze-file")
def analyze_document(file: UploadFile = File(...)):
    """Accept a PDF, extract its text, then run the identical analysis pipeline.

    Declared as a normal `def` so FastAPI runs it in a threadpool - the blocking
    work (model encode, psycopg2, LLM call) must not stall the event loop.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported.")

    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="The PDF is larger than the 20 MB limit.",
        )

    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            page_texts = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Could not read the PDF. It may be corrupt or encrypted.",
        ) from exc

    text = "\n".join(page_texts).strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail="No selectable text found. Scanned PDFs need OCR before they can be analysed.",
        )

    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS]

    return run_analysis(text)
