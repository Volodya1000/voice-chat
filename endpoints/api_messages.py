from fastapi import APIRouter, UploadFile, HTTPException, Depends
from dependency_injector.wiring import inject, Provide

from containers import Container
from services.document_service import DocumentService

router = APIRouter(prefix="/api/chats", tags=["Documents"])


@router.post("/{chat_id}/upload")
@inject
async def upload_document(
    chat_id: int,
    file: UploadFile,
    document_service: DocumentService = Depends(Provide[Container.document_service]),
):
    """
    Эндпоинт загрузки документа (PDF/DOCX):
    - парсит файл,
    - разбивает на чанки,
    - создаёт эмбеддинги,
    - сохраняет в Qdrant.
    """
    try:
        file_bytes = await file.read()
        await document_service.process_and_store(chat_id, file.filename, file_bytes)
        return {"status": "ok", "filename": file.filename}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке файла: {e}")


@router.get("/{chat_id}/search")
@inject
async def search_chunks(
    chat_id: int,
    query: str,
    document_service: DocumentService = Depends(Provide[Container.document_service]),
):
    """
    Поиск релевантных чанков по текстовому запросу в Qdrant.
    """
    results = document_service.search(chat_id, query)
    return results
