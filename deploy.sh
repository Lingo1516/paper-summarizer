#!/bin/bash
# Paper Summarizer 部署腳本
# 用途：OpenClaw 接手部署用
# 狀態：前端已完稿，後端需要一個能跑長時間請求的 host

set -e

echo "=== Paper Summarizer 部署開始 ==="

# 1. 檢查必要工具
which node python3 cloudflared uvicorn 2>/dev/null
echo "檢查完成"

# 2. 啟動後端（異步任務模式，適合長時間 AI 分析）
cd ~/paper-summarizer
cat > .env << 'EOF'
LLM_API_KEY=***
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=deepseek/deepseek-chat
CORS_ORIGINS=*
EOF

nohup uvicorn api:app --host 0.0.0.0 --port 8010 > /tmp/paper-summarizer.log 2>&1 &
sleep 3
curl -s http://127.0.0.1:8010/health && echo " 后端啟動完成"

# 3. 啟動 Cloudflare Tunnel（永久固定網址）
# 注意：這是臨時方案，要固定網域需先配 Cloudflare DNS
nohup cloudflared tunnel --url http://127.0.0.1:8010 --no-autoupdate > /tmp/cloudflared.log 2>&1 &
sleep 10

# 4. 讀取 Tunnel URL
TUNNEL_URL=$(grep -o 'https://[^ ]*\.trycloudflare\.com' /tmp/cloudflared.log | head -1)
echo "=== 部署完成 ==="
echo "前端: https://lingo1516.github.io/paper-summarizer/"
echo "後端: $TUNNEL_URL"
echo ""
echo "注意：此 Tunnel URL 是臨時的，重開後會改變。長期方案請：
1. 註冊 Cloudflare 帳號
2. 建立固定的 Tunnel（需 DNS 控制權）
3. 或直接部署到 Railway / Render"
