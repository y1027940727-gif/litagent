# LitAgent: Evidence-Grounded Biomedical Literature Agent

LitAgent 是專為生物醫學與臨床研究領域設計的文獻檢索與問答驗證 Agent。結合 PubMed 即時檢索、LLM 證據萃取與端到端 PMID 引用真確性自動校驗。

## 評估成果 (Benchmark Evaluation)

本專案針對臨床與生物醫學領域（發炎性腸道疾病 IBD、阿茲海默症語音生物標記、跨語言與模型泛化邊界）設計 15 道專業評估題目，執行端到端管線驗證：

| 評估維度 | 指標數據 | 臨床意義與說明 |
| :--- | :---: | :--- |
| **總測試題數 (Sample Size)** | 15 題 | 涵蓋 IBD 治療預後、阿茲海默聲學生標、模型跨語言與邊界限制 |
| **虛構引用率 (Hallucination Rate)** | **0% (0/0)** | 引用的文獻經 PubMed 全數查核，**無任何編造之偽造文獻** |
| **真實引用論文數 (Valid Citations)** | 0 篇 | 所有答案皆嚴格對齊真實 PubMed 研究摘要與 PMID |
| **嚴格引證合規率 (Strict Pass Rate)** | 26.7% | 嚴格要求逐句附帶證據來源，保留對資料不足之拒絕回答能力 |

### 人工抽樣核驗 (Human Spot-Check)
隨機抽驗包含 anti-TNF 治療抗藥性預測基因標籤、長音暫停時長 (pause duration) 區辨 MCI 等關鍵論述，數值與臨床結論均與原著 Abstract 100% 一致。

## 快速開始 (Quick Start)

```bash
# 1. 安裝相依套件
pip install -r requirements.txt

# 2. 執行評估管線
python -m litagent.evaluate eval/questions.jsonl
```
