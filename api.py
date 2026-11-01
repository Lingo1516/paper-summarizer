from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import json
import tempfile
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

# Use NVIDIA API (free tier)
client = OpenAI(
    api_key=os.getenv("NVIDIA_API_KEY", "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"),
    base_url="https://integrate.api.nvidia.com/v1"
)

SYSTEM_PROMPT_ZH = """你是學術論文分析專家。請分析以下PDF論文內容，產出結構化摘要。
只輸出JSON，不要有其他文字。格式：
{
  "title": "論文標題",
  "authors": ["作者1", "作者2"],
  "abstract": "200字摘要",
  "objectives": ["目標1", "目標2"],
  "methods": "研究方法描述",
  "key_findings": ["發現1", "發現2", "發現3"],
  "conclusion": "100字結論"
}"""

SYSTEM_PROMPT_EN = """You are an academic paper analysis expert. Analyze the following PDF paper and produce a structured summary.
Output ONLY JSON, no other text. Format:
{
  "title": "Paper Title",
  "authors": ["Author 1", "Author 2"],
  "abstract": "200 word summary",
  "objectives": ["Objective 1", "Objective 2"],
  "methods": "Research methodology description",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
  "conclusion": "100 word conclusion"
}"""

@app.post("/summarize")
async def summarize_paper(
    file: UploadFile = File(...),
    format: str = Form("markdown"),
    language: str = Form("zh")
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")
    
    # Read PDF
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        with pdfplumber.open(tmp_path) as pdf:
            pages = []
            for page in pdf.pages[:10]:
                text = page.extract_text()
                if text:
                    pages.append(text)
            pdf_text = "\n\n".join(pages)
    finally:
        os.unlink(tmp_path)
    
    if not pdf_text.strip():
        raise HTTPException(400, "Could not extract text from PDF")
    
    # Call AI
    system_prompt = SYSTEM_PROMPT_ZH if language == "zh" else SYSTEM_PROMPT_EN
    try:
        response = client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"論文內容：\n{pdf_text[:10000]}"}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        ai_output = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(500, f"AI API error: {str(e)}")
    
    # Parse JSON
    try:
        # Try to extract JSON from response
        if "```json" in ai_output:
            ai_output = ai_output.split("```json")[1].split("```")[0]
        elif "```" in ai_output:
            ai_output = ai_output.split("```")[1].split("```")[0]
        result = json.loads(ai_output.strip())
    except:
        result = {
            "title": "Paper Summary",
            "authors": [],
            "abstract": ai_output[:500],
            "objectives": [],
            "methods": "",
            "key_findings": [],
            "conclusion": ""
        }
    
    return result

@app.get("/health")
async def health():
    return {"status": "ok"}
