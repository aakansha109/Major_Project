from fastapi import APIRouter, HTTPException
from app.models.retrieval import RetrievalQuery, RetrievalResult
from app.services.retrieval_service import retrieval_service

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])

@router.post("", response_model=RetrievalResult)
def retrieve_memory(query: RetrievalQuery):
    """
    Multi-stage temporal and semantic retrieval:
    1. Temporal validity filter
    2. Semantic vector cosine similarity
    3. 1-hop / 2-hop neighborhood expansion
    """
    try:
        return retrieval_service.retrieve(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")
