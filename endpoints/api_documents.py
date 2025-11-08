# endpoints/api_documents.py
from fastapi import APIRouter, UploadFile, HTTPException, Query, Depends
from dependency_injector.wiring import inject, Provide

from containers import Container
from services.document_service import DocumentService

router = APIRouter(prefix="/api/chats", tags=["Documents"])


@router.post("/{chat_id}/upload", response_model=dict)
@inject
async def upload_document(
    chat_id: int,
    file: UploadFile,
    document_service: DocumentService = Depends(Provide[Container.document_service]),
):
    try:
        file_bytes = await file.read()
        result = await document_service.process_and_store(chat_id, file.filename, file_bytes)
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")


@router.get("/{chat_id}/search", response_model=dict)
@inject
async def search_document(
    chat_id: int,
    query: str = Query(..., min_length=1),
    document_service: DocumentService = Depends(Provide[Container.document_service]),
):
    try:
        results = await document_service.search(chat_id, query)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {e}")
