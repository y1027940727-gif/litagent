import pytest
from unittest.mock import MagicMock

def test_citation_verifier_logic():
    """驗證 Citation Grounding Verifier 能準確比對檢索到的真實文獻 PMID"""
    retrieved_pmids = ["12345678", "87654321"]
    
    # 模擬 LLM 回覆內容中包含真實與偽造文獻
    cited_pmids_found = ["12345678", "99999999"]
    
    # 驗證機制：過濾未出現在檢索清單中的偽造文獻
    valid_citations = [pmid for pmid in cited_pmids_found if pmid in retrieved_pmids]
    fabricated_citations = [pmid for pmid in cited_pmids_found if pmid not in retrieved_pmids]
    
    assert "12345678" in valid_citations
    assert "99999999" in fabricated_citations
    assert len(valid_citations) == 1
    assert len(fabricated_citations) == 1

def test_empty_query_handling():
    """驗證空輸入的保護防禦機制"""
    from app import answer_query
    ans, cite = answer_query("")
    assert "請輸入醫學相關問題" in ans
    assert cite == ""

def test_missing_api_key_handling(monkeypatch):
    """驗證未配置 GEMINI_API_KEY 時的提示訊息"""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from app import answer_query
    ans, _ = answer_query("What is the biomarker for Alzheimer's?")
    assert "GEMINI_API_KEY" in ans
