from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os, json, tempfile, uuid, time, threading, yaml
from openai import OpenAI
import pdfplumber

app = FastAPI(title="Paper Summarizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- LLM ----------
def get_client():
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")
    if not api_key:
        try:
            cfg = yaml.safe_load(open(os.path.expanduser("~/.hermes/config.yaml")))
            prov = cfg["providers"]["openrouter"]
            api_key = prov["api_key"]
            base_url = prov.get("base_url") or base_url
        except Exception:
            pass
    if not api_key:
        raise RuntimeError("No LLM API key configured")
    return OpenAI(api_key=api_key, base_url=base_url), model


SYSTEM_PROMPT = {
    "zh": """你是學術論文分析專家。仔細閱讀論文內容後，只輸出JSON（繁體中文），不要任何其他文字：
{"title":"論文標題","authors":["作者1","作者2"],"abstract":"200-300字摘要","objectives":["研究目標1","研究目標2"],"methods":"研究方法描述","key_findings":["關鍵發現1","關鍵發現2","關鍵發現3"],"conclusion":"100-150字結論"}""",
    "en": """You are an academic paper analysis expert. Read the paper carefully and output ONLY JSON (English), no other text:
{"title":"Paper Title","authors":["Author 1","Author 2"],"abstract":"200-300 word summary","objectives":["Objective 1","Objective 2"],"methods":"Research methodology","key_findings":["Finding 1","Finding 2","Finding 3"],"conclusion":"100-150 word conclusion"}""",
}

EMPTY = {"title": "", "authors": [], "abstract": "", "objectives": [],
         "methods": "", "key_findings": [], "conclusion": ""}

def parse_json_response(raw: str) -> dict:
    txt = raw.strip()
    if "```json" in txt:
        txt = txt.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in txt:
        txt = txt.split("```", 1)[1].split("```", 1)[0]
    txt = txt.strip()
    s, e = txt.find("{"), txt.rfind("}")
    if s != -1 and e > s:
        txt = txt[s:e + 1]
    return json.loads(txt)


def extract_pdf(path: str, max_pages: int = 12) -> tuple[str, int]:
    with pdfplumber.open(path) as pdf:
        chunks = []
        for page in pdf.pages[:max_pages]:
            t = page.extract_text()
            if t:
                chunks.append(t)
        return "\n\n".join(chunks), len(pdf.pages)


def run_job(job_id: str, pdf_path: str, language: str, max_pages: int, filename: str):
    try:
        JOBS[job_id]["stage"] = "reading_pdf"
        text, total_pages = extract_pdf(pdf_path, max_pages)
        if len(text.strip()) < 100:
            JOBS[job_id].update(status="error",
                error="無法從 PDF 擷取足夠文字（可能是掃描圖檔或加密檔案，需先 OCR）")
            return

        JOBS[job_id]["stage"] = "analyzing"
        client, model = get_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.get(language, SYSTEM_PROMPT["zh"])},
                {"role": "user", "content": f"論文內容：\n{text[:14000]}"},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content

        try:
            result = parse_json_response(raw)
        except Exception as e:
            print(f"[WARN] parse failed {e}: {raw[:400]}", flush=True)
            result = dict(EMPTY)
            result["title"] = filename
            result["abstract"] = raw[:1500]

        for k, v in EMPTY.items():
            result.setdefault(k, v)
        if isinstance(result.get("authors"), str):
            result["authors"] = [result["authors"]]
        for k in ("objectives", "key_findings"):
            if isinstance(result.get(k), str):
                result[k] = [result[k]]

        result["_meta"] = {
            "pages_read": min(max_pages, total_pages),
            "pages_total": total_pages,
            "chars": len(text),
            "model": model,
            "filename": filename,
        }
        JOBS[job_id].update(status="done", result=result, stage="done")
    except Exception as e:
        JOBS[job_id].update(status="error", error=str(e)[:400])
    finally:
        try:
            os.unlink(pdf_path)
        except Exception:
            pass
        JOBS[job_id]["updated"] = time.time()


JOBS: dict[str, dict] = {}


def cleanup_old():
    now = time.time()
    for jid in [k for k, v in JOBS.items() if now - v.get("updated", now) > 3600]:
        JOBS.pop(jid, None)


# ---------- endpoints ----------
@app.post("/summarize")
async def summarize_submit(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    format: str = Form("markdown"),
    language: str = Form("zh"),
    max_pages: int = Form(12),
):
    """送出分析任務，立刻回傳 job_id（避開 Cloudflare 100 秒限制）"""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(400, "PDF too large (max 25MB)")

    cleanup_old()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    job_id = uuid.uuid4().hex
    JOBS[job_id] = {
        "status": "pending", "stage": "queued",
        "created": time.time(), "updated": time.time(),
    }
    background.add_task(run_job, job_id, tmp_path, language, max_pages, file.filename)
    return {"job_id": job_id, "status": "pending"}


@app.get("/result/{job_id}")
async def get_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found or expired")
    if job["status"] == "done":
        return job["result"]
    if job["status"] == "error":
        return JSONResponse(status_code=500, content={"detail": job.get("error", "failed")})
    return JSONResponse(status_code=202, content={
        "status": job["status"], "stage": job.get("stage", "")
    })


@app.get("/health")
async def health():
    return {"status": "ok", "jobs": len(JOBS)}
