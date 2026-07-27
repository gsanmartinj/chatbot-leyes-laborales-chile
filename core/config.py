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

# Puntaje mínimo (0-1) para que un fragmento se considere relevante en la
# búsqueda semántica. Fragmentos por debajo de este umbral se descartan.
MIN_SCORE: float = float(os.getenv("MIN_SCORE", "0.30"))
# Máximo de fragmentos a devolver cuando se consulta un artículo específico.
MAX_ARTICLE_CHUNKS: int = int(os.getenv("MAX_ARTICLE_CHUNKS", "12"))

# --- Motor de redacción (opcional) ------------------------------------------
# Si hay un proveedor configurado, las respuestas se redactan a partir de los
# fragmentos recuperados localmente (RAG). Sin proveedor, la app funciona 100%
# local mostrando los fragmentos tal cual.
#   auto     -> usa DeepSeek si hay LLM_API_KEY; si no, Gemini; si no, local
#   deepseek | gemini | none -> fuerza esa opción
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto").strip().lower()

# Endpoint compatible con OpenAI (DeepSeek V4 Pro servido por NVIDIA NIM).
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-ai/deepseek-v4-pro")

# Alternativa: Gemini. Clave gratuita en https://aistudio.google.com/apikey
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- Administración ----------------------------------------------------------
# Contraseña para el panel de Gradio. Cambiar en el archivo .env para producción.
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "cambia-esta-clave")

# Aviso legal que se muestra en las respuestas.
LEGAL_DISCLAIMER: str = (
    "*Esta información proviene de los documentos cargados y tiene fines "
    "orientativos. No constituye asesoría legal. Para casos particulares, "
    "consulte a un abogado o a la Dirección del Trabajo.*"
)
