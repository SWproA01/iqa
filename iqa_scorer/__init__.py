# 파일 이름: iqa_scorer/__init__.py

# 필요한 라이브러리 설치 확인 및 임포트
IQA_AVAILABLE = False
try:
    import torch
    from .scorer_engine import HybridScorer 
    IQA_AVAILABLE = True
except ImportError as e:

    print(f"⚠️ IQA 기능 라이브러리 로드 실패. AI 품질 검사 비활성화: {e}")

hybrid_scorer = None
if IQA_AVAILABLE:
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        hybrid_scorer = HybridScorer(device=device) # 객체 생성
    except Exception as e:
        # 모델 다운로드 실패 등 런타임 오류 시 처리
        print(f"❌ HybridScorer 초기화 중 오류: {e}")
        hybrid_scorer = None
        IQA_AVAILABLE = False