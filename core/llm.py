"""Redacción de respuestas con un modelo de lenguaje (opcional).

Soporta dos proveedores:

- **deepseek**: cualquier endpoint compatible con OpenAI (por defecto DeepSeek
  V4 Pro servido por NVIDIA NIM).
- **gemini**: API de Google.

Es totalmente opcional: si no hay proveedor configurado o falta el paquete
correspondiente, `llm_available()` devuelve False y la app sigue funcionando en
modo 100% local (mostrando los fragmentos crudos).

En ambos casos el modelo recibe ÚNICAMENTE los fragmentos recuperados de los PDF
del usuario y redacta con ellos. No usa conocimiento externo (se le instruye
explícitamente), por lo que la respuesta queda anclada a los documentos.
"""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Dict, List, Optional

from .config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LEGAL_DISCLAIMER,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
)

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


def _has_package(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


def active_provider() -> Optional[str]:
    """Devuelve el proveedor efectivo: 'deepseek', 'gemini' o None (modo local)."""
    if LLM_PROVIDER == "none":
        return None

    deepseek_ok = bool(LLM_API_KEY) and _has_package("openai")
    gemini_ok = bool(GEMINI_API_KEY) and _has_package("google.genai")

    if LLM_PROVIDER == "deepseek":
        return "deepseek" if deepseek_ok else None
    if LLM_PROVIDER == "gemini":
        return "gemini" if gemini_ok else None

    # auto: se prefiere DeepSeek si está configurado.
    if deepseek_ok:
        return "deepseek"
    if gemini_ok:
        return "gemini"
    return None


def llm_available() -> bool:
    """Indica si hay un modelo configurado para redactar respuestas."""
    return active_provider() is not None


def provider_label() -> str:
    """Nombre legible del motor activo, para mostrar en la interfaz."""
    provider = active_provider()
    if provider == "deepseek":
        # "deepseek-ai/deepseek-v4-pro" -> "Deepseek V4 Pro"
        nombre = LLM_MODEL.split("/")[-1].replace("-", " ").strip()
        return nombre.title()
    if provider == "gemini":
        return GEMINI_MODEL.replace("-", " ").title()
    return "Local"


def _build_context(hits: List[Dict[str, object]]) -> str:
    """Arma el bloque de contexto con los fragmentos y sus citas."""
    lineas = []
    for i, hit in enumerate(hits, start=1):
        cita = f"[Fragmento {i}] {hit.get('source', '?')}, pág. {hit.get('page', '?')}"
        if hit.get("articulo"):
            cita += f", Art. {hit['articulo']}"
        lineas.append(f"{cita}\n{hit.get('texto', '')}")
    return "\n\n".join(lineas)


def _user_prompt(question: str, hits: List[Dict[str, object]]) -> str:
    return (
        f"Pregunta del usuario:\n{question}\n\n"
        f"Fragmentos de los documentos (única fuente permitida):\n\n"
        f"{_build_context(hits)}\n\n"
        "Redacta la respuesta siguiendo las reglas."
    )


# --- Proveedor: endpoint compatible con OpenAI (DeepSeek) --------------------
def _es_transitorio(exc: Exception) -> bool:
    """¿El fallo parece pasajero y vale la pena reintentar?"""
    codigo = getattr(exc, "status_code", None)
    if codigo in (404, 408, 409, 429, 500, 502, 503, 504):
        return True
    # Errores de red/timeout sin código HTTP asociado.
    return codigo is None and isinstance(exc, (OSError, TimeoutError))



@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI

    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=90.0)


def _generate_deepseek(question: str, hits: List[Dict[str, object]]) -> str:
    # La pasarela devuelve 404/5xx de forma intermitente aunque el modelo exista,
    # así que se reintenta antes de degradar al modo local.
    intentos = 3
    for intento in range(1, intentos + 1):
        try:
            response = _openai_client().chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_INSTRUCTION},
                    {"role": "user", "content": _user_prompt(question, hits)},
                ],
                temperature=0.2,
                max_tokens=900,
            )
            break
        except Exception as exc:  # noqa: BLE001
            if intento == intentos or not _es_transitorio(exc):
                raise
            time.sleep(1.2 * intento)

    mensaje = response.choices[0].message
    texto = (mensaje.content or "").strip()
    if not texto:
        # Algunos modelos de razonamiento dejan el texto en otro campo.
        texto = (getattr(mensaje, "reasoning_content", "") or "").strip()
    if not texto:
        raise RuntimeError("El modelo devolvió una respuesta vacía.")
    return texto


# --- Proveedor: Gemini -------------------------------------------------------
@lru_cache(maxsize=1)
def _gemini_client():
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def _generate_gemini(question: str, hits: List[Dict[str, object]]) -> str:
    from google.genai import types

    response = _gemini_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=_user_prompt(question, hits),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            temperature=0.2,
        ),
    )
    texto = (response.text or "").strip()
    if not texto:
        raise RuntimeError("El modelo devolvió una respuesta vacía.")
    return texto


def generate_answer(question: str, hits: List[Dict[str, object]]) -> str:
    """Redacta una respuesta a partir de los fragmentos recuperados.

    Lanza una excepción si la llamada falla (el llamador decide el fallback a
    modo local).
    """
    provider = active_provider()
    if provider == "deepseek":
        texto = _generate_deepseek(question, hits)
    elif provider == "gemini":
        texto = _generate_gemini(question, hits)
    else:
        raise RuntimeError("No hay un modelo de redacción configurado.")
    return f"{texto}\n\n{LEGAL_DISCLAIMER}"


# Alias retrocompatible con la versión anterior del módulo.
gemini_available = llm_available
