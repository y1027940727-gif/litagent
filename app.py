import sys
import os

# Hot-patch: 解決 huggingface_hub 新版移除 HfFolder 導致 gradio[oauth] 崩潰的問題
try:
    import huggingface_hub
    if not hasattr(huggingface_hub, "HfFolder"):
        class MockHfFolder:
            @staticmethod
            def get_token():
                return os.getenv("HF_TOKEN") or None
            @staticmethod
            def save_token(token):
                pass
            @staticmethod
            def delete_token():
                pass
        huggingface_hub.HfFolder = MockHfFolder
except Exception:
    pass

import gradio as gr
from litagent.agent import Agent
from litagent.llm import Gemini

def answer_query(question):
    if not question or not question.strip():
        return "請輸入醫學相關問題。", ""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "系統未設定 GEMINI_API_KEY，請在 Space Settings -> Secrets 中確認配置。", ""
    
    try:
        agent = Agent(Gemini(model="gemini-flash-lite-latest", api_key=api_key))
        res = agent.run(question.strip())
        citations = res.check.get("cited", [])
        
        cite_text = "### 引用真實文獻檢驗\n"
        if citations:
            for pmid in citations:
                raw_id = pmid.replace("PMID:", "").strip()
                cite_text += f"- [{pmid}](https://pubmed.ncbi.nlm.nih.gov/{raw_id})\n"
        else:
            cite_text += "無特定單篇引用（或檢索證據不足保留回答）"
            
        return res.answer, cite_text
    except Exception as e:
        return f"執行錯誤: {str(e)}", ""

demo = gr.Interface(
    fn=answer_query,
    inputs=gr.Textbox(
        lines=3,
        placeholder="例如: What acoustic features in spontaneous speech show sensitivity for Alzheimer's?",
        label="臨床與生醫文獻問題 (Clinical Query)"
    ),
    outputs=[
        gr.Markdown(label="LitAgent 回答 (Evidence-based Answer)"),
        gr.Markdown(label="PubMed 檢索文獻真實驗證 (Ground Truth Citations)")
    ],
    title="🧬 LitAgent: Evidence-Grounded Biomedical Literature Agent",
    description="結合 PubMed API 即時檢索與端到端反幻覺校驗（0% 偽造引用），專注於 IBD 與神經退化性疾病數位生物標記。",
    examples=[
        ["What acoustic features in spontaneous speech show the highest sensitivity for detecting early-stage Alzheimer's disease?"],
        ["What are the primary predictors of primary non-response to anti-TNF therapy in Crohn's disease patients?"],
        ["What serum biomarkers best correlate with endoscopic mucosal healing in active ulcerative colitis?"]
    ]
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
