# endpoints/web_actions.py
from fastapi import (
    APIRouter, Request, Depends, Form,
    HTTPException, BackgroundTasks, UploadFile, File, Body
)
from fastapi.responses import (
    Response, JSONResponse,
    StreamingResponse
)
from pydantic import BaseModel, confloat, validator
# Это зависимость из `pip install sse-starlette`
from sse_starlette.sse import EventSourceResponse
import asyncio
import io
from dependency_injector.wiring import inject, Provide
from containers import Container
# Импортируем Broadcaster для внедрения в SSE-эндпоинт
from services.chat_service import ChatService, Broadcaster
from services.transcription_service import TranscriptionService
from gtts import gTTS
from .utils import get_current_user_id_from_request
from services.local_tts_service import LocalTextToVoiceService

router = APIRouter()


@router.post("/chats/{chat_id}/send")
@inject
async def send_message(
        request: Request,
        chat_id: int,
        background_tasks: BackgroundTasks,
        content: str = Form(...),
        chat_service: ChatService = Depends(Provide[Container.chat_service])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    background_tasks.add_task(
        chat_service.process_user_message,
        chat_id=chat_id,
        content=content,
        user_id=user_id
    )

    return Response(status_code=204)

# ЭНДПОИНТ ДЛЯ ТРАНСКРИПЦИИ АУДИО-
@router.post("/chats/transcribe_voice")
@inject
async def transcribe_voice(
        request: Request,
        audio_file: UploadFile = File(...),
        transcription_service: TranscriptionService = Depends(Provide[Container.transcription_service])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not audio_file.content_type or not audio_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an audio file.")

    try:
        user_prompt = await transcription_service.transcribe_audio(audio_file)
        return JSONResponse({"content": user_prompt})
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Критическая ошибка обработки аудио: {e}")


@router.get("/chats/{chat_id}/events")
@inject
async def sse_chat_events(
        request: Request,
        chat_id: int,
        broadcaster: Broadcaster = Depends(Provide[Container.broadcaster])
):
    user_id = get_current_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async def event_generator():
        """Генератор, который слушает очередь и отправляет данные клиенту."""
        queue = await broadcaster.subscribe(chat_id)
        try:
            while True:
                # Ждем новое событие (словарь) из очереди
                event_data_dict = await queue.get()

                yield event_data_dict

        except asyncio.CancelledError:
            # Клиент отключился
            broadcaster.unsubscribe(chat_id, queue)
            raise

    return EventSourceResponse(event_generator())

class TTSRequest(BaseModel):
    text: str
    speaker: str = "aidar"
    speed: float = 1.0
    pitch_semitones: float = 0
    gain_db: float = 0
    reverb_time: float = 0
    reverb_decay: float = 0

@router.post("/tts", response_class=StreamingResponse)
@inject
async def text_to_speech(
    request: Request,
    tts_req: TTSRequest = Body(...),  # теперь принимаем JSON
    tts_service: "LocalTextToVoiceService" = Depends(Provide[Container.local_tts_service])
):
    """
    Локальный TTS с использованием Silero (вместо gTTS).
    """

    user_id = get_current_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not tts_req.text.strip():
        raise HTTPException(status_code=400, detail="Text content is required.")

    try:
        audio_bytes = tts_service.synthesize_to_bytes(
            text=tts_req.text,
            speaker=tts_req.speaker,
            speed=tts_req.speed,
            pitch_semitones=tts_req.pitch_semitones,
            gain_db=tts_req.gain_db,
            reverb_time=tts_req.reverb_time,
            reverb_decay=tts_req.reverb_decay,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"TTS synthesis error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при генерации речи.")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=tts_audio.wav"}
    )
