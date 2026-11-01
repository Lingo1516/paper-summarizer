// Cloudflare Worker - Paper Summarizer API Proxy
// 部署：wrangler deploy
// 環境變數：NVIDIA_API_KEY 需設在 Cloudflare Secrets

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405, headers: CORS });
    }

    try {
      const formData = await request.formData();
      const file = formData.get('file');
      const language = formData.get('language') || 'zh';

      if (!file) {
        return new Response(JSON.stringify({ error: 'No file uploaded' }), {
          status: 400,
          headers: { ...CORS, 'Content-Type': 'application/json' },
        });
      }

      // Read PDF bytes → base64
      const buffer = await file.arrayBuffer();
      const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));

      // Extract text client-side is not possible in Worker; use pdf.js via AI or
      // send to NVIDIA with document understanding if available.
      // Fallback: use simple text extraction heuristic on raw bytes.
      const text = extractTextHeuristic(buffer);

      if (!text || text.length < 50) {
        return new Response(JSON.stringify({
          error: '無法從 PDF 擷取文字，可能是掃描檔或加密檔案'
        }), {
          status: 400,
          headers: { ...CORS, 'Content-Type': 'application/json' },
        });
      }

      const systemPrompt = language === 'zh'
        ? `你是學術論文分析專家。分析論文內容，只輸出JSON：
{"title":"標題","authors":["作者"],"abstract":"200字摘要","objectives":["目標"],"methods":"方法","key_findings":["發現"],"conclusion":"結論"}`
        : `You are an academic paper analysis expert. Analyze the paper, output ONLY JSON:
{"title":"Title","authors":["Author"],"abstract":"200 word summary","objectives":["Objective"],"methods":"Methods","key_findings":["Finding"],"conclusion":"Conclusion"}`;

      const aiRes = await fetch('https://integrate.api.nvidia.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${env.NVIDIA_API_KEY}`,
        },
        body: JSON.stringify({
          model: 'nvidia/llama-3.1-nemotron-70b-instruct',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: `論文內容：\n${text.slice(0, 12000)}` },
          ],
          temperature: 0.3,
          max_tokens: 1500,
        }),
      });

      if (!aiRes.ok) {
        const err = await aiRes.text();
        return new Response(JSON.stringify({ error: `AI API error: ${err}` }), {
          status: 502,
          headers: { ...CORS, 'Content-Type': 'application/json' },
        });
      }

      const aiData = await aiRes.json();
      let content = aiData.choices?.[0]?.message?.content || '';

      // Strip markdown fences
      if (content.includes('```json')) {
        content = content.split('```json')[1].split('```')[0];
      } else if (content.includes('```')) {
        content = content.split('```')[1].split('```')[0];
      }

      let result;
      try {
        result = JSON.parse(content.trim());
      } catch {
        result = {
          title: 'Paper Summary',
          authors: [],
          abstract: content.slice(0, 800),
          objectives: [],
          methods: '',
          key_findings: [],
          conclusion: '',
        };
      }

      return new Response(JSON.stringify(result), {
        headers: { ...CORS, 'Content-Type': 'application/json' },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { ...CORS, 'Content-Type': 'application/json' },
      });
    }
  },
};

// 極簡 PDF 文字擷取：抓取 PDF 中 ( ) 之間的文字物件
// 對「正常文字型 PDF」有效；掃描圖檔需 OCR
function extractTextHeuristic(buffer) {
  const bytes = new Uint8Array(buffer);
  let raw = '';
  // Latin-1 decode
  for (let i = 0; i < bytes.length; i++) {
    raw += String.fromCharCode(bytes[i]);
  }

  // 嘗試找 FlateDecode 串流外的 Tj/TJ 文字運算子
  const chunks = [];
  const tjRe = /\((?:\\.|[^\\)])*\)\s*Tj/g;
  const tjArrRe = /\[((?:\((?:\\.|[^\\)])*\)|[^\]])*)\]\s*TJ/g;

  let m;
  while ((m = tjRe.exec(raw)) !== null) {
    chunks.push(m[0].replace(/\)\s*Tj$/, '').slice(1).replace(/\\([()\\])/g, '$1'));
  }
  while ((m = tjArrRe.exec(raw)) !== null) {
    const inner = m[1];
    const parts = inner.match(/\((?:\\.|[^\\)])*\)/g) || [];
    chunks.push(parts.map(p => p.slice(1, -1).replace(/\\([()\\])/g, '$1')).join(''));
  }

  let text = chunks.join(' ').replace(/\s+/g, ' ').trim();

  // 若太少（多數 PDF 內容在壓縮串流中），退回抓可讀 ASCII 片段
  if (text.length < 200) {
    const asciiRuns = raw.match(/[\x20-\x7E]{30,}/g) || [];
    text = asciiRuns
      .filter(s => !/^(endobj|stream|xref|startxref|%PDF)/.test(s))
      .join(' ')
      .slice(0, 20000);
  }

  return text;
}
