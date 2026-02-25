import csv
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .models import EmailRegistration

# ── Rutas ────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR    = BASE_DIR / "static"
CSV_PATH      = BASE_DIR / "usuarios.csv"

# ── App FastAPI ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="SonoLit — Landing Page",
    description="Página de preventa del proyecto de Sonorización Literaria",
    version="1.0.0",
)

# Archivos estáticos y templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _ensure_csv() -> None:
    """Crea el CSV con encabezados si no existe."""
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["email", "fecha_registro"])


def _email_exists(email: str) -> bool:
    """Verifica si el email ya está registrado."""
    if not CSV_PATH.exists():
        return False
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # saltar encabezado
        return any(row[0] == email for row in reader if row)


# ── Rutas ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Sirve la landing page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/register")
async def register_email(data: EmailRegistration):
    """
    Registra un correo electrónico en usuarios.csv.
    Valida con Pydantic (EmailStr) y evita duplicados.
    """
    _ensure_csv()

    if _email_exists(data.email):
        return JSONResponse(
            status_code=409,
            content={"detail": "Este correo ya está registrado."},
        )

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([data.email, datetime.now().isoformat()])

    return {"message": "¡Registro exitoso!", "email": data.email}
