// Cloudflare Worker — Paper Summarizer API Proxy
// 功能：接收前端傳來的 PDF 文字 + 語言，呼叫 AI API，回傳結構化摘要
//
// 部署步驟：
// 1. 登入 Cloudflare Dashboard → Workers & Pages
// 2. 建立新 Worker，貼上此程式碼
// 3. 設定環境變數：
//    - API_KEY = 你的 OpenRouter API Key（sk-or-...）
//    - API_BASE = https://openrouter.ai/api/v1 （預設）
//    - MODEL = deepseek/deepseek-chat （預設）

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
}

export default {
  async fetch(request, env) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS })
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { 
        status: 405,
        headers: CORS 
      })
    }

    try {
      const body = await request.json()
      const { text, language = 'zh', prompt: customPrompt } = body

      if (!text || text.length < 100) {
        return Response.json(
          { error: 'PDF 文字過短，請確認檔案是否可讀' },
          { status: 400, headers: CORS }
        )
      }

      // Use custom prompt or default
      const systemPrompt = customPrompt || getSystemPrompt(language)
      const apiKey = env.API_KEY
      const apiBase = env.API_BASE || 'https://openrouter.ai/api/v1'
      const model = env.MODEL || 'deepseek/deepseek-chat'

      if (!apiKey) {
        return Response.json(
          { error: 'API Key 未設定，請在 Worker 環境變數中設定 API_KEY' },
          { status: 500, headers: CORS }
        )
      }

      // Call AI API
      const aiResponse = await fetch(`${apiBase}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
          'HTTP-Referer': request.headers.get('Origin') || 'https://paper-summarizer.lingo1516.github.io',
          'X-Title': 'Paper Summarizer',
        },
        body: JSON.stringify({
          model: model,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: `論文內容：\n${text.slice(0, 12000)}` },
          ],
          temperature: 0.3,
          max_tokens: 2000,
        }),
      })

      if (!aiResponse.ok) {
        const errText = await aiResponse.text()
        console.error('AI API error:', errText)
        return Response.json(
          { error: `AI API 錯誤: ${errText.slice(0, 200)}` },
          { status: 502, headers: CORS }
        )
      }

      const aiData = await aiResponse.json()
      let content = aiData.choices?.[0]?.message?.content || ''

      // Strip markdown code fences if present
      if (content.includes('```json')) {
        content = content.split('```json')[1].split('```')[0]
      } else if (content.includes('```')) {
        content = content.split('```')[1].split('```')[0]
      }
      content = content.trim()

      // Parse JSON response
      let result
      try {
        result = JSON.parse(content)
      } catch {
        // Fallback: try to extract JSON object from response
        const match = content.match(/\{[\s\S]*\}/)
        if (match) {
          try {
            result = JSON.parse(match[0])
          } catch {
            result = {
              title: 'Paper Summary',
              authors: [],
              abstract: content.slice(0, 800),
              objectives: [],
              methods: '',
              key_findings: [],
              conclusion: '',
            }
          }
        } else {
          result = {
            title: 'Paper Summary',
            authors: [],
            abstract: content.slice(0, 800),
            objectives: [],
            methods: '',
            key_findings: [],
            conclusion: '',
          }
        }
      }

      // Ensure consistent shape
      const finalResult = {
        title: result.title || '',
        authors: Array.isArray(result.authors) ? result.authors : [],
        abstract: result.abstract || '',
        objectives: Array.isArray(result.objectives) ? result.objectives : [],
        methods: result.methods || '',
        key_findings: Array.isArray(result.key_findings) ? result.key_findings : [],
        conclusion: result.conclusion || '',
        meta: {
          language,
          model,
          chars: text.length,
          timestamp: new Date().toISOString(),
        }
      }

      return Response.json(finalResult, { headers: CORS })

    } catch (err) {
      console.error('Worker error:', err)
      return Response.json(
        { error: err.message || 'Internal server error' },
        { status: 500, headers: CORS }
      )
    }
  }
}

function getSystemPrompt(language) {
  if (language === 'en') {
    return `You are an academic paper analysis expert. Read the paper carefully and output ONLY valid JSON, no other text:
{
  "title": "Paper Title",
  "authors": ["Author 1", "Author 2"],
  "abstract": "200-300 word summary of the paper",
  "objectives": ["Research objective 1", "Research objective 2"],
  "methods": "Brief description of research methodology",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
  "conclusion": "100-150 word conclusion"
}`
  }
  
  return `你是學術論文分析專家。仔細閱讀論文內容後，只輸出JSON（繁體中文），不要任何其他文字：
{
  "title": "論文標題",
  "authors": ["作者1", "作者2"],
  "abstract": "200-300字摘要",
  "objectives": ["研究目標1", "研究目標2"],
  "methods": "研究方法描述",
  "key_findings": ["關鍵發現1", "關鍵發現2", "關鍵發現3"],
  "conclusion": "100-150字結論"
}`
}
