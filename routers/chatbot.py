"""
Router del chatbot con IA para TechStock.
Endpoints JSON para consultas al asistente inteligente.
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import require_auth
from services.chatbot_service import chatbot_service
import models

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])


class ChatMessage(BaseModel):
    message: str
    history: list = []


@router.post("/ask")
async def ask_chatbot(
    payload: ChatMessage,
    request: Request,
    user: models.Usuario = Depends(require_auth),
):
    """Envia una pregunta al chatbot. Intenta IA, cae a offline."""
    result = await chatbot_service.ask(payload.message, payload.history, user.id)
    return JSONResponse(result)


@router.get("/status")
async def chatbot_status(
    request: Request,
    user: models.Usuario = Depends(require_auth),
):
    """Verifica si la IA esta disponible."""
    return JSONResponse(
        {
            "ai_available": chatbot_service.is_available(),
            "mode": "gemini" if chatbot_service.is_available() else "offline",
        }
    )
