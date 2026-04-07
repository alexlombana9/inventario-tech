"""
Router del chatbot con IA para TechStock.
Endpoints JSON para consultas al asistente inteligente.
Incluye servicio Gemini API con fallback offline.
"""
import httpx
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import require_auth
from config import settings
import models

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])


# ── System Prompt ───────────────────────────────────────────

SYSTEM_PROMPT = """Eres el asistente virtual de TechStock, un software de inventario y punto de venta
desarrollado por Orionics. Tu nombre es "Asistente TechStock".

PERSONALIDAD:
- Eres como un companero de trabajo amigable que conoce el software a la perfeccion
- Hablas de forma natural, cercana y con calidez, como si fueras una persona real
- Usas un tono conversacional, NO robotico ni de manual
- Puedes usar expresiones naturales como "Claro!", "Con gusto te explico", "Buena pregunta!"
- Si no sabes algo, se honesto: "Eso no lo tengo claro, pero puedo ayudarte con..."
- Responde SIEMPRE en espanol
- Adapta la longitud de tu respuesta a la complejidad de la pregunta
- Para preguntas simples, responde en 1-2 oraciones. Para temas complejos, explayate un poco mas
- Cuando sea util, indica la ruta en el software (ej: "Ve a Inventario > Productos")
- NUNCA inventes funcionalidades que no existen en TechStock
- NUNCA compartas codigo fuente, SQL, o detalles tecnicos internos
- Si te preguntan algo que NO tiene relacion con TechStock, redirige amablemente:
  "Eso se sale un poco de mi area, pero estoy aqui para ayudarte con todo lo de TechStock. En que te puedo echar una mano?"

MODULOS DE TECHSTOCK:
- Productos: CRUD, codigo unico por local, referencia, precio costo/venta/minimo, stock, unidades de medida
- Categorias: Agrupacion de productos, soft delete con proteccion cascade
- Inventario: Entradas, salidas, ajustes de stock, historial de movimientos
- Proveedores: CRUD, NIT/RUC, detalle con deudas asociadas
- Clientes: CRUD, documento, historial de compras, saldo credito
- Ventas/POS: Punto de venta, busqueda productos, descuentos, precio manual, metodos pago (Efectivo/Tarjeta/Transferencia/Credito), anulacion con reversion de stock
- Caja: Apertura con monto inicial, cierre con conteo, movimientos (ingresos/egresos), historial, diferencia
- Deudas (Cuentas por Pagar): CRUD, pagos parciales, estados (PENDIENTE/PARCIAL/PAGADO), vencimiento, acreedores
- Facturas (Cuentas por Cobrar): CRUD, cobros parciales, importacion desde Excel, estados
- Acreedores: Tipos (Proveedor/Banco/Persona/Otro)
- Gastos: CRUD, categorias (Arriendo/Servicios/Nomina/etc), tipo Directo/Indirecto
- Reportes: Stock actual, stock bajo, movimientos, exportacion Excel y PDF
- Dashboard: Metricas resumen, 7 graficas Chart.js, filtro por fechas
- Usuarios: Roles (SUPERADMIN/ADMIN/VENDEDOR/BODEGUERO), permisos custom por modulo
- Configuracion: Nombre negocio, NIT, moneda, recibo personalizado (por local)
- Backup: Crear/restaurar backups completos de base de datos
- Importar Excel: Categorias, productos, facturas desde archivos .xlsx
- Auditoria: Log permanente de todas las acciones con filtros
- Multi-tenant: Multiples locales/sucursales, datos completamente aislados por local
- Atajos: Ctrl+K abre la paleta de comandos para navegacion rapida
- Chatbot: Boton flotante de ayuda en esquina inferior derecha

ROLES Y ACCESO:
- SUPERADMIN: Todo + gestion de locales y dashboard consolidado
- ADMIN: Todo dentro de su local asignado
- VENDEDOR: Dashboard, productos (ver), ventas/POS, clientes, caja, finanzas, reportes
- BODEGUERO: Dashboard, productos, categorias, inventario, proveedores, reportes
"""


# ── Chatbot Service ─────────────────────────────────────────

class ChatbotService:
    """Servicio de chatbot con IA (Gemini) y fallback offline."""

    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.chatbot_ai_model
        self.enabled = settings.chatbot_ai_enabled
        self._rate_limits = {}  # user_id -> [timestamps]

    def is_available(self):
        """Verifica si la IA esta disponible (tiene API key y esta habilitada)."""
        return bool(self.api_key) and self.enabled

    async def ask(self, message, history, user_id):
        """Metodo principal — intenta IA primero, cae a offline si falla."""
        if not self._check_rate_limit(user_id):
            return {
                "response": "Has alcanzado el limite de consultas. Intenta de nuevo en unos minutos.",
                "source": "system",
            }

        msg = message.strip()
        if len(msg) < 3:
            return {
                "response": "Por favor escribe una pregunta mas detallada.",
                "source": "system",
            }
        if len(msg) > 500:
            return {
                "response": "Tu mensaje es demasiado largo. Intenta ser mas conciso.",
                "source": "system",
            }

        if self.is_available():
            try:
                ai_response = await self._ask_ai(msg, history)
                if ai_response:
                    return {"response": ai_response, "source": "ai"}
            except httpx.TimeoutException:
                return {
                    "response": "La respuesta esta tardando demasiado. Intenta de nuevo en un momento.",
                    "source": "system",
                }
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429:
                    return {
                        "response": "Se alcanzo el limite de la API. Intenta de nuevo en unos minutos.",
                        "source": "system",
                    }
                return {
                    "response": "Hubo un problema al conectar con la IA. Intenta de nuevo.",
                    "source": "system",
                }
            except Exception:
                return {
                    "response": "Ocurrio un error inesperado. Intenta de nuevo.",
                    "source": "system",
                }

        return {"response": None, "source": "offline"}

    async def _ask_ai(self, message, history):
        """Llama a la API de Gemini."""
        contents = []
        for msg in (history or [])[-6:]:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {"maxOutputTokens": 800, "temperature": 0.85, "topP": 0.92},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        return None

    def _check_rate_limit(self, user_id, max_per_hour=20):
        """Verifica que el usuario no exceda el limite de consultas por hora."""
        now = datetime.now()
        cutoff = now - timedelta(hours=1)
        timestamps = self._rate_limits.get(user_id, [])
        timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= max_per_hour:
            return False
        timestamps.append(now)
        self._rate_limits[user_id] = timestamps
        return True


chatbot_service = ChatbotService()


# ── Endpoints ───────────────────────────────────────────────

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
