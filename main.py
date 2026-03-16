from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import anthropic
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Real Estate AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, cambia esto a tu dominio
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ---------------------------------------------------------------------------
# Datos de ejemplo de la inmobiliaria (en producción vendría de una BD)
# ---------------------------------------------------------------------------
AGENCY_DATA = {
    "name": "Inmobiliaria Ejemplo",
    "agent_name": "Carlos López",
    "agent_email": os.environ.get("AGENT_EMAIL", "agente@ejemplo.com"),
    "properties": [
        {
            "id": "P001",
            "title": "Piso luminoso en Chamberí",
            "type": "piso",
            "operation": "venta",
            "price": 320000,
            "size_m2": 85,
            "rooms": 3,
            "bathrooms": 2,
            "floor": "4º con ascensor",
            "zone": "Chamberí, Madrid",
            "description": "Piso completamente reformado, cocina nueva, parquet en toda la vivienda.",
            "community_fees": 120,
            "available": True,
        },
        {
            "id": "P002",
            "title": "Ático con terraza en Malasaña",
            "type": "ático",
            "operation": "venta",
            "price": 480000,
            "size_m2": 100,
            "rooms": 3,
            "bathrooms": 2,
            "floor": "6º último",
            "zone": "Malasaña, Madrid",
            "description": "Ático con terraza de 40m², vistas despejadas, garaje incluido.",
            "community_fees": 180,
            "available": True,
        },
        {
            "id": "P003",
            "title": "Piso en alquiler en Lavapiés",
            "type": "piso",
            "operation": "alquiler",
            "price": 1100,
            "size_m2": 60,
            "rooms": 2,
            "bathrooms": 1,
            "floor": "2º sin ascensor",
            "zone": "Lavapiés, Madrid",
            "description": "Piso acogedor, reformado, muy bien comunicado con metro.",
            "community_fees": 0,
            "available": True,
        },
    ],
}

SYSTEM_PROMPT = f"""Eres un asistente virtual de {AGENCY_DATA['name']}, una agencia inmobiliaria profesional.
Tu objetivo es ayudar a los visitantes de la web a encontrar el inmueble que buscan, responder sus dudas y, si están interesados en visitar, recoger sus datos de contacto.

INMUEBLES DISPONIBLES:
{json.dumps(AGENCY_DATA['properties'], ensure_ascii=False, indent=2)}

TU FLUJO DE CONVERSACIÓN:
1. Saluda de forma amigable y pregunta qué tipo de inmueble buscan (compra o alquiler, zona, presupuesto aproximado).
2. Muestra los inmuebles que encajen. Sé concreto: precio, metros, habitaciones, zona.
3. Responde cualquier duda sobre los inmuebles (gastos de comunidad, planta, estado, etc.).
4. Cuando notes interés real, precalifica con naturalidad:
   - ¿Es para uso propio o inversión?
   - ¿Tienen hipoteca aprobada o necesitan financiación?
   - ¿Cuándo querrían mudarse aproximadamente?
5. Si el lead es caliente (tiene presupuesto, urgencia y quiere visitar), recoge:
   - Nombre completo
   - Teléfono
   - Días/horario preferido para visitar
   Confirma que {AGENCY_DATA['agent_name']} les contactará para confirmar la visita.
6. Si el lead es frío (solo mirando, sin presupuesto claro), sé amable, ofrece resolver dudas y despídete sin presionar.

REGLAS:
- Sé natural, cálido y profesional. Nada de respuestas robóticas.
- Nunca inventes información que no esté en los datos de los inmuebles.
- Si preguntan algo que no sabes, di que se lo consultarás al agente.
- Cuando hayas recogido los datos de contacto de un lead caliente, incluye al final de tu respuesta exactamente este bloque JSON (invisible para el usuario):
  [LEAD_DATA]{{"name":"...","phone":"...","property_id":"...","visit_preference":"...","notes":"..."}}[/LEAD_DATA]
- Responde siempre en español.
- Sé conciso: respuestas cortas y claras, no párrafos interminables.
"""

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------
class Message(BaseModel):
    role: str  # "user" o "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    lead_captured: bool = False
    lead_data: Optional[dict] = None

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def extract_lead_data(text: str):
    """Extrae el bloque JSON de lead si el agente lo ha incluido."""
    import re
    match = re.search(r'\[LEAD_DATA\](.*?)\[/LEAD_DATA\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None

def clean_reply(text: str) -> str:
    """Elimina el bloque de lead data del texto visible al usuario."""
    import re
    return re.sub(r'\[LEAD_DATA\].*?\[/LEAD_DATA\]', '', text, flags=re.DOTALL).strip()

def send_lead_email(lead_data: dict):
    """Envía un email al agente con los datos del lead capturado."""
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not all([smtp_host, smtp_user, smtp_pass]):
        print(f"[LEAD CAPTURADO] {json.dumps(lead_data, ensure_ascii=False)}")
        return  # En desarrollo solo logueamos

    property_info = next(
        (p for p in AGENCY_DATA["properties"] if p["id"] == lead_data.get("property_id")), {}
    )

    body = f"""
    🏠 NUEVO LEAD CAPTURADO
    
    Nombre: {lead_data.get('name', 'No indicado')}
    Teléfono: {lead_data.get('phone', 'No indicado')}
    Inmueble de interés: {property_info.get('title', lead_data.get('property_id', 'No indicado'))}
    Preferencia de visita: {lead_data.get('visit_preference', 'No indicado')}
    Notas: {lead_data.get('notes', '-')}
    
    Contacta pronto — este lead está caliente.
    """

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = AGENCY_DATA["agent_email"]
    msg["Subject"] = f"🏠 Nuevo lead: {lead_data.get('name', 'Desconocido')}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL(smtp_host, 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, AGENCY_DATA["agent_email"], msg.as_string())
        print(f"[EMAIL ENVIADO] Lead: {lead_data.get('name')}")
    except Exception as e:
        print(f"[ERROR EMAIL] {e}")

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "agent": AGENCY_DATA["name"]}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No hay mensajes")

    # Convertir al formato de Anthropic
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del agente: {str(e)}")

    raw_reply = response.content[0].text

    # Detectar y procesar lead capturado
    lead_data = extract_lead_data(raw_reply)
    clean = clean_reply(raw_reply)

    if lead_data:
        send_lead_email(lead_data)

    return ChatResponse(
        reply=clean,
        lead_captured=lead_data is not None,
        lead_data=lead_data,
    )

@app.get("/properties")
def get_properties():
    return AGENCY_DATA["properties"]
