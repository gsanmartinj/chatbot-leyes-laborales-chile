"""Redacción de respuestas con Gemini (opcional).

Este módulo es totalmente opcional: si no hay GEMINI_API_KEY configurada o el
paquete `google-genai` no está instalado, `gemini_available()` devuelve False y
la app sigue funcionando en modo 100% local (mostrando los fragmentos crudos).

Cuando está activo, Gemini recibe ÚNICAMENTE los fragmentos recuperados de los
PDF del usuario y redacta con ellos una respuesta en lenguaje natural. No usa
conocimiento externo (se le instruye explícitamente), por lo que la respuesta
queda anclada a los documentos cargados.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

from .config import GEMINI_API_KEY, GEMINI_MODEL, LEGAL_DISCLAIMER

# Instrucción de sistema: obliga a responder solo con base en los fragmentos.
_SYSTEM_INSTRUCTION = (
    "Eres un asistente que responde preguntas sobre leyes laborales de Chile. "
    "Debes responder ÚNICAMENTE con base en los fragmentos de documentos que se "
    "te entregan. Reglas estrictas:\n"
    "1. No uses conocimiento externo ni inventes información. Si los fragmentos "
    "no contienen la respuesta, dilo claramente ('No encontré esa información en "
    "los documentos cargados').\n"
    "2. Cita siempre el documento, la página y el número de artículo cuando "
    "aparezcan en los fragmentos.\n"
    "3. Responde en español, de forma clara, ordenada y concisa.\n"
    "4. No entregues asesoría legal definitiva; la información es orientativa."
)


def gemini_available() -> bool:
    """Indica si Gemini está configurado y disponible para usarse."""
    if not GEMINI_API_KEY:
        return False
    try:
        import google.genai  # noqa: F401
    except ImportError:
        return False
    return True


@lru_cache(maxsize=1)
def _get_client():
    """Cliente de Gemini (cacheado por proceso)."""
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def _build_context(hits: List[Dict[str, object]]) -> str:
    """Arma el bloque de contexto con los fragmentos y sus citas."""
    lineas = []
    for i, hit in enumerate(hits, start=1):
        cita = f"[Fragmento {i}] {hit.get('source', '?')}, pág. {hit.get('page', '?')}"
        if hit.get("articulo"):
            cita += f", Art. {hit['articulo']}"
        lineas.append(f"{cita}\n{hit.get('texto', '')}")
    return "\n\n".join(lineas)


def generate_answer(question: str, hits: List[Dict[str, object]]) -> str:
    """Redacta una respuesta con Gemini a partir de los fragmentos recuperados.

    Lanza una excepción si la llamada a la API falla (el llamador decide el
    fallback a modo local).
    """
    from google.genai import types

    contexto = _build_context(hits)
    prompt = (
        f"Pregunta del usuario:\n{question}\n\n"
        f"Fragmentos de los documentos (única fuente permitida):\n\n{contexto}\n\n"
        "Redacta la respuesta siguiendo las reglas."
    )

    client = _get_client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            temperature=0.2,
        ),
    )

    texto = (response.text or "").strip()
    if not texto:
        raise RuntimeError("Gemini devolvió una respuesta vacía.")
    return f"{texto}\n\n{LEGAL_DISCLAIMER}"
