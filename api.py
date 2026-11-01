from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import tempfile
import json
from openai import OpenAI
import pdfplumber

load_dotenv()

app = FastAPI(title="Paper Summarizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_ZH = """你是學術論文分析專家。請分析以下PDF論文內容，產出結構化摘要。

格式要求（繁體中文）：
1. **標題**：論文標題
2. **作者**：所有作者
3. **摘要**：200-300字精華摘要
4. **研究目標**：1-3點
5. **方法**：簡述研究方法
6. **關鍵發現**：3-5個重點發現
7. **結論**：100-150字結論

請用JSON格式回覆，不要有其他文字。"""

PROMPT_EN = """You are an academic paper analysis expert. Analyze the following PDF paper and produce a structured summary.

Format requirements (English):
1. **Title**: Paper title
2. **Authors**: All authors
3. **Abstract**: 200-300 word summary
4. **Research Objectives**: 1-3 points
5. **Methods**: Brief research methodology
6. **Key Findings**: 3-5 key findings
7. **Conclusion**: 100-150 word conclusion

Reply in JSON format only, no other text."""

@app.post("/summarize")
async def summarize_paper(file: UploadFile = File(...), format: str = "markdown", language: str = "zh"):
    # 讀取 PDF
    content = ""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        with pdfplumber.open(tmp_path) as pdf:
            pages = []
            for page in pdf.pages[:10]:  # 限制前10頁
                text = page.extract_text()
                if text:
                    pages.append(text)
            pdf_text = "\n\n".join(pages)
    finally:
        os.unlink(tmp_path)
    
    if not pdf_text.strip():
        raise HTTPException(status_code=400, detail="無法讀取PDF文字")
    
    # 調用 AI
    prompt = PROMPT_ZH if language == "zh" else PROMPT_EN
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes academic papers."},
            {"role": "user", "content": f"{prompt}\n\n論文內容：\n{pdf_text[:8000]}"}
        ],
        temperature=0.3,
        max_tokens=1500
    )
    
    ai_output = response.choices[0].message.content
    
    # 解析 JSON
    try:
        result = json.loads(ai_output)
    except:
        # fallback: 簡單的 text 解析
        result = {
            "title": "Paper Summary",
            "authors": [],
            "summary": ai_output,
            "key_findings": [],
            "methods": "",
            "conclusion": ""
        }
    
    return result

@app.get("/health")
async def health():
    return {"status": "ok"}
