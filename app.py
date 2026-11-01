import streamlit as st
import requests
import json
import os

st.set_page_config(page_title="Paper Summarizer", page_icon="📄", layout="wide")

st.title("📄 Paper Summarizer")
st.markdown("Upload a PDF paper and get an AI-generated summary in seconds.")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Settings")
    output_format = st.selectbox("Output Format", ["markdown", "json", "html"])
    language = st.selectbox("Language", ["zh", "en"])
    
    api_url = st.text_input("API URL", "http://localhost:8000")
    
    st.markdown("---")
    st.markdown("**How to use:**\n1. Upload a PDF\n2. Click Summarize\n3. Download results")

# Upload area
uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

if uploaded_file is not None:
    st.success(f"✅ Uploaded: {uploaded_file.name}")
    
    if st.button("🧠 Summarize with AI", type="primary"):
        with st.spinner("Analyzing paper... this may take a moment"):
            try:
                files = {'file': (uploaded_file.name, uploaded_file, 'application/pdf')}
                params = {'format': output_format, 'language': language}
                
                response = requests.post(
                    f"{api_url}/summarize",
                    files=files,
                    params=params,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display results
                    st.subheader("📋 Summary")
                    st.markdown(f"**Title:** {result.get('title', 'N/A')}")
                    if result.get('authors'):
                        st.markdown(f"**Authors:** {', '.join(result['authors'])}")
                    st.divider()
                    
                    if 'summary' in result:
                        st.markdown("### Abstract")
                        st.markdown(result['summary'])
                    
                    if 'key_findings' in result:
                        st.markdown("### Key Findings")
                        for i, finding in enumerate(result['key_findings'], 1):
                            st.markdown(f"{i}. {finding}")
                    
                    if 'methods' in result:
                        st.markdown("### Methods")
                        st.markdown(result['methods'])
                    
                    if 'conclusion' in result:
                        st.markdown("### Conclusion")
                        st.markdown(result['conclusion'])
                    
                    # Download buttons
                    col1, col2, col3 = st.columns(3)
                    
                    filename = uploaded_file.name.rsplit('.', 1)[0]
                    
                    with col1:
                        if st.button("📥 JSON"):
                            st.download_button(
                                "Download JSON",
                                data=json.dumps(result, indent=2, ensure_ascii=False),
                                file_name=f"summary_{filename}.json",
                                mime="application/json"
                            )
                    
                    with col2:
                        if st.button("📥 Markdown"):
                            md = f"# {result.get('title', 'Paper Summary')}\n\n"
                            if result.get('authors'):
                                md += f"**Authors:** {', '.join(result['authors'])}\n\n"
                            md += "## Abstract\n\n"
                            md += result.get('summary', '') + "\n\n"
                            if result.get('key_findings'):
                                md += "## Key Findings\n\n"
                                for f in result['key_findings']:
                                    md += f"- {f}\n"
                                md += "\n"
                            if result.get('methods'):
                                md += "## Methods\n\n"
                                md += result['methods'] + "\n\n"
                            if result.get('conclusion'):
                                md += "## Conclusion\n\n"
                                md += result['conclusion']
                            
                            st.download_button(
                                "Download Markdown",
                                data=md,
                                file_name=f"summary_{filename}.md",
                                mime="text/markdown"
                            )
                    
                    with col3:
                        if st.button("📥 HTML"):
                            html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>{result.get('title', 'Paper Summary')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .meta {{ color: #666; font-style: italic; }}
    </style>
</head>
<body>
    <h1>{result.get('title', 'Paper Summary')}</h1>
    <p class="meta">Authors: {', '.join(result.get('authors', []))}</p>
    <hr>
    <h2>Abstract</h2>
    <p>{result.get('summary', '')}</p>
    <h2>Key Findings</h2>
    <ul>{''.join(f'<li>{f}</li>' for f in result.get('key_findings', []))}</ul>
    <h2>Methods</h2>
    <p>{result.get('methods', '')}</p>
    <h2>Conclusion</h2>
    <p>{result.get('conclusion', '')}</p>
</body>
</html>"""
                            st.download_button(
                                "Download HTML",
                                data=html,
                                file_name=f"summary_{filename}.html",
                                mime="text/html"
                            )
                            
                else:
                    st.error(f"❌ Error: {response.status_code}")
                    st.error(response.text)
                    
            except Exception as e:
                st.error(f"❌ Failed: {e}")

else:
    st.info("👆 Please upload a PDF file to get started")

st.markdown("---")
st.markdown("**Built with Streamlit + FastAPI + OpenAI**")
