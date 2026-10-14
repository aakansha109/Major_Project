from fastapi import APIRouter, HTTPException
from app.models.inference import InferenceRequest, InferenceResponse
from app.services.inference_service import inference_service

router = APIRouter(prefix="/inference", tags=["Inference"])

@router.post("", response_model=InferenceResponse)
def infer_task(req: InferenceRequest):
    """
    Temporal Task Inference:
    Answers natural language queries using temporal interval bounds,
    identifying historical transitions and generating grounded answers.
    """
    try:
        return inference_service.infer_answer(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
