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

# Instrucción de sistema: define la fuente (solo los fragmentos), el tono formal
# y el público objetivo (personas sin formación jurídica).
_SYSTEM_INSTRUCTION = (
    "Eres un asistente que responde preguntas sobre leyes laborales de Chile. "
    "Tu público son personas naturales (trabajadores y trabajadoras) SIN "
    "conocimientos en derecho.\n\n"
    "FUENTE DE INFORMACIÓN (regla absoluta):\n"
    "- Responde ÚNICAMENTE con base en los fragmentos de documentos que se te "
    "entregan. No uses conocimiento externo ni inventes información.\n"
    "- Si los fragmentos no contienen la respuesta, indícalo claramente: "
    "'No encontré esa información en los documentos cargados'. No la completes "
    "con suposiciones.\n\n"
    "TONO Y ESTILO:\n"
    "- Formal y respetuoso, tratando a la persona de 'usted'. Sin coloquialismos, "
    "sin humor, sin emojis.\n"
    "- Conciso: ve directo al punto. Como referencia, no más de 150 palabras "
    "salvo que la pregunta exija detallar varios supuestos.\n"
    "- Lenguaje sencillo y claro, apto para alguien sin formación jurídica. "
    "Evita el lenguaje técnico; si un término legal es inevitable, explícalo "
    "brevemente entre paréntesis la primera vez que lo uses.\n"
    "- No transcribas el texto legal completo: explica con tus palabras lo que "
    "significa para la persona.\n\n"
    "FORMATO:\n"
    "- Comienza con una respuesta directa en una o dos frases.\n"
    "- Si hay condiciones, plazos o requisitos, agrégalos como viñetas breves.\n"
    "- Cita siempre el documento, la página y el número de artículo cuando "
    "aparezcan en los fragmentos.\n\n"
    "LÍMITES:\n"
    "- La información es orientativa y no constituye asesoría legal definitiva.\n"
    "- Si la consulta excede lo que dicen los documentos o requiere evaluar un "
    "caso particular, sugiera consultar a un abogado o a la Dirección del Trabajo."
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
