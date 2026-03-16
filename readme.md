# Real Estate AI Agent

Agente de IA para inmobiliarias pequeñas. Responde FAQs, precalifica leads y notifica al agente cuando hay un contacto serio.

## Qué hace

- Responde preguntas sobre los inmuebles disponibles (precio, metros, zona, gastos)
- Precalifica al visitante (compra/alquiler, presupuesto, urgencia, hipoteca)
- Recoge datos de contacto cuando el lead está caliente
- Envía email automático al agente con el resumen del lead

## Stack

- **Backend:** FastAPI + Python
- **IA:** Claude (Anthropic)
- **Deploy:** Render
- **Embebible:** widget de chat en cualquier web via `<script>`

## Instalación local

```bash
# 1. Clona el repo
git clone https://github.com/tuusuario/realestate-agent
cd realestate-agent

# 2. Crea entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Instala dependencias
pip install -r requirements.txt

# 4. Configura variables de entorno
cp .env.example .env
# Edita .env con tu API key de Anthropic y email del agente

# 5. Arranca el servidor
uvicorn src.main:app --reload
```

El servidor corre en `http://localhost:8000`

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/chat` | Enviar mensaje al agente |
| GET | `/properties` | Listar inmuebles |

### Ejemplo de llamada a /chat

```json
POST /chat
{
  "messages": [
    {"role": "user", "content": "Hola, busco un piso de 2 habitaciones en Madrid"}
  ]
}
```

## Deploy en Render

1. Sube el código a GitHub
2. En Render: New → Web Service → conecta tu repo
3. Render detecta `render.yaml` automáticamente
4. Añade las variables de entorno en el panel de Render:
   - `ANTHROPIC_API_KEY`
   - `AGENT_EMAIL`
   - (opcional) `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`
5. Deploy — en 2 minutos tienes la URL pública

## Personalizar para cada inmobiliaria

Edita el bloque `AGENCY_DATA` en `src/main.py`:
- Nombre de la agencia y del agente
- Lista de inmuebles con sus características
- Email del agente para recibir leads

En una versión futura esto puede venir de una base de datos o un panel de administración.

## Embeber en cualquier web

Una vez desplegado, añade este script donde quieras que aparezca el chat:

```html
<!-- Pega esto justo antes de </body> -->
<script>
  window.REALESTATE_AGENT_URL = "https://tu-app.onrender.com";
</script>
<script src="https://tu-app.onrender.com/widget.js"></script>
```

(El widget.js se construye en la siguiente fase del proyecto)
