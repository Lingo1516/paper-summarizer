import { NextRequest, NextResponse } from "next/server";

export const config = {
  runtime: "edge",
  maxDuration: 60,
};

export async function POST(req: NextRequest) {
  const apiKey = process.env.NVIDIA_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { error: "Server configuration error" },
      { status: 500 }
    );
  }

  const formData = await req.formData();
  const text = (formData.get("text") as string) || "";

  if (!text) {
    return NextResponse.json(
      { error: "No content provided" },
      { status: 400 }
    );
  }

  const prompt = `你是學術論文分析專家。請分析以下論文，用繁體中文產出結構化摘要，用 JSON 格式回覆：

{
  "標題": "論文標題",
  "作者": "作者名單",
  "摘要": "200-300字研究摘要",
  "研究目的": "研究目標與問題",
  "方法": "研究方法概述",
  "關鍵發現": ["發現1", "發現2", "發現3"],
  "結論": "主要結論",
  "貢獻": "對領域的貢獻"
}

只回 JSON，不要有其他文字。

論文內容：
${text.slice(0, 8000)}`;

  try {
    const res = await fetch(
      "https://integrate.api.nvidia.com/v1/chat/completions",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "z-ai/glm-5.3-flash",
          messages: [
            { role: "system", content: "You are a helpful assistant." },
            { role: "user", content: prompt },
          ],
          temperature: 0.3,
          max_tokens: 2000,
        }),
      }
    );

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json({ error: data }, { status: res.status });
    }

    const content = data.choices?.[0]?.message?.content || "";
    return NextResponse.json({ text: content });
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
