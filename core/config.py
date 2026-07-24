"""Configuración central del proyecto.

Define rutas absolutas (para que las dos apps compartan la misma base de datos
sin importar desde qué carpeta se ejecuten), el modelo de embeddings, la colección
de ChromaDB y la contraseña del panel de administración.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env si existe.
load_dotenv()

# --- Rutas -------------------------------------------------------------------
# Raíz del proyecto = carpeta que contiene este paquete "core".
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
PDF_DIR: Path = DATA_DIR / "pdfs"          # copia de los PDF originales subidos
CHROMA_DIR: Path = DATA_DIR / "chroma"     # base vectorial persistente

# Crear las carpetas de datos si no existen.
PDF_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# --- Base vectorial y embeddings --------------------------------------------
COLLECTION_NAME: str = "leyes_laborales"

# Modelo multilingüe con buen soporte de español. Se descarga una sola vez
# desde HuggingFace (~120 MB) y luego funciona sin conexión.
EMBED_MODEL: str = os.getenv(
    "EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# --- Parámetros de búsqueda / chunking --------------------------------------
TOP_K: int = int(os.getenv("TOP_K", "5"))          # fragmentos a devolver por consulta
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))       # caracteres por fragmento
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))  # solapamiento entre fragmentos

# --- Administración ----------------------------------------------------------
# Contraseña para el panel de Gradio. Cambiar en el archivo .env para producción.
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "cambia-esta-clave")

# Aviso legal que se muestra en las respuestas.
LEGAL_DISCLAIMER: str = (
    "⚠️ Esta información proviene de los documentos cargados y tiene fines "
    "orientativos. No constituye asesoría legal. Para casos concretos consulta "
    "a un abogado o a la Dirección del Trabajo."
)
