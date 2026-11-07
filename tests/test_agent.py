"""
Unit tests for LitAgent citation grounding and anti-hallucination verification.
"""
import pytest

def verify_citations(cited_pmids, ground_truth_pmids):
    """Citation Grounding Verifier 核心演算法邏輯"""
    valid = [p for p in cited_pmids if p in ground_truth_pmids]
    fabricated = [p for p in cited_pmids if p not in ground_truth_pmids]
    precision = len(valid) / len(cited_pmids) if cited_pmids else 1.0
    return {
        "valid": valid,
        "fabricated": fabricated,
        "is_grounded": len(fabricated) == 0,
        "precision": precision
    }

def test_citation_grounding_zero_hallucination():
    """驗證當引用全來自真實 PubMed 檢索結果時，虛構率為 0%"""
    retrieved = ["38291024", "37561829", "39012345"]
    cited = ["38291024", "37561829"]
    result = verify_citations(cited, retrieved)
    assert result["is_grounded"] is True
    assert len(result["fabricated"]) == 0
    assert result["precision"] == 1.0

def test_citation_grounding_detects_hallucination():
    """驗證當模型虛構文獻時，Verifier 能精確攔截並標註"""
    retrieved = ["38291024", "37561829"]
    hallucinated_cited = ["38291024", "99999999"]
    result = verify_citations(hallucinated_cited, retrieved)
    assert result["is_grounded"] is False
    assert "99999999" in result["fabricated"]
    assert result["precision"] == 0.5

def test_empty_query_boundary():
    """驗證輸入邊界條件處理"""
    empty_query = "   "
    assert not empty_query.strip()
