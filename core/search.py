"""Búsqueda híbrida sobre la base vectorial.

Dos modos:
- Si la pregunta menciona un artículo concreto ("artículo 1", "art. 12"), se
  filtra **exactamente** ese artículo por metadato (resultado preciso).
- En caso contrario, búsqueda **semántica** por embeddings, descartando los
  fragmentos poco relevantes según un umbral.

No genera texto nuevo: solo recupera y presenta lo que está en los documentos.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .config import LEGAL_DISCLAIMER, MAX_ARTICLE_CHUNKS, MIN_SCORE, TOP_K
from .db import get_collection
from .embeddings import embed_query

_ORDINALS = {
    "primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5,
    "sexto": 6, "septimo": 7, "séptimo": 7, "octavo": 8, "noveno": 9,
    "decimo": 10, "décimo": 10, "undecimo": 11, "undécimo": 11,
    "duodecimo": 12, "duodécimo": 12, "unico": 1, "único": 1,
}

# Detecta una referencia a artículo en la pregunta del usuario.
_ART_QUERY_RE = re.compile(
    r"\bart[íi]culo?s?\.?\s*(\d{1,4}|" + "|".join(_ORDINALS.keys()) + r")\b",
    re.IGNORECASE,
)


def detect_article(question: str) -> Optional[int]:
    """Devuelve el número de artículo mencionado en la pregunta, o None."""
    m = _ART_QUERY_RE.search(question or "")
    if not m:
        return None
    token = m.group(1).lower()
    if token.isdigit():
        return int(token)
    return _ORDINALS.get(token)


def _search_by_article(article: int) -> List[Dict[str, object]]:
    """Recupera de forma exacta los fragmentos de un artículo, ordenados."""
    collection = get_collection()
    got = collection.get(
        where={"articulo": article}, include=["documents", "metadatas"]
    )
    docs = got.get("documents") or []
    metas = got.get("metadatas") or []

    hits: List[Dict[str, object]] = []
    for text, meta in zip(docs, metas):
        meta = meta or {}
        hits.append(
            {
                "texto": text,
                "source": meta.get("source", "desconocido"),
                "page": meta.get("page", "?"),
                "articulo": meta.get("articulo"),
                "seq": meta.get("seq", 0),
                "score": 1.0,
            }
        )
    # Ordenar por su posición original en el documento.
    hits.sort(key=lambda h: h.get("seq", 0))
    return hits[:MAX_ARTICLE_CHUNKS]


def _search_semantic(question: str, top_k: int) -> List[Dict[str, object]]:
    """Búsqueda por similitud semántica, filtrando por umbral de relevancia."""
    collection = get_collection()
    result = collection.query(
        query_embeddings=[embed_query(question)],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]

    hits: List[Dict[str, object]] = []
    for text, meta, dist in zip(docs, metas, dists):
        meta = meta or {}
        score = max(0.0, 1.0 - float(dist))
        hits.append(
            {
                "texto": text,
                "source": meta.get("source", "desconocido"),
                "page": meta.get("page", "?"),
                "articulo": meta.get("articulo"),
                "score": round(score, 3),
            }
        )

    # Quedarse con los relevantes; si ninguno supera el umbral, devolver el mejor.
    relevantes = [h for h in hits if h["score"] >= MIN_SCORE]
    return relevantes if relevantes else hits[:1]


def search(question: str, top_k: int = TOP_K) -> List[Dict[str, object]]:
    """Busca los fragmentos más relevantes para la pregunta (modo híbrido).

    Returns:
        lista de dicts {"texto", "source", "page", "articulo", "score"}.
    """
    question = (question or "").strip()
    if not question:
        return []

    collection = get_collection()
    if collection.count() == 0:
        return []

    # Modo 1: pregunta por un artículo específico -> filtro exacto.
    article = detect_article(question)
    if article is not None:
        hits = _search_by_article(article)
        if hits:
            return hits
        # Si no existe ese artículo indexado, caer a búsqueda semántica.

    # Modo 2: búsqueda semántica.
    return _search_semantic(question, top_k)


def answer(question: str, top_k: int = TOP_K) -> Dict[str, object]:
    """Devuelve la respuesta lista para mostrar, con su modo y fuentes.

    Si hay un modelo configurado, redacta la respuesta a partir de los fragmentos
    recuperados; si no (o si la llamada falla), usa el modo local mostrando los
    fragmentos tal cual.

    Returns:
        dict {"text": markdown, "hits": fragmentos, "mode": "llm"|"local"|"local-fallback"}.
    """
    hits = search(question, top_k=top_k)

    # Import diferido para no requerir los paquetes del proveedor en modo local.
    from .llm import generate_answer, llm_available

    if hits and llm_available():
        try:
            return {"text": generate_answer(question, hits), "hits": hits, "mode": "llm"}
        except Exception as exc:  # noqa: BLE001 - ante cualquier fallo, caer a local
            texto = (
                f"*No fue posible redactar la respuesta con el modelo ({exc}). "
                "Se muestran los fragmentos encontrados.*\n\n" + format_answer(hits)
            )
            return {"text": texto, "hits": hits, "mode": "local-fallback"}

    return {"text": format_answer(hits), "hits": hits, "mode": "local"}


def format_answer(hits: List[Dict[str, object]]) -> str:
    """Arma una respuesta legible en Markdown a partir de los fragmentos."""
    if not hits:
        return (
            "No encontré información relacionada en los documentos cargados. "
            "Prueba reformular la pregunta o pide al administrador que suba PDF "
            "sobre el tema.\n\n" + LEGAL_DISCLAIMER
        )

    partes = ["Esto es lo que encontré en los documentos cargados:\n"]
    for i, hit in enumerate(hits, start=1):
        cita = f"*{hit['source']}* — pág. {hit['page']}"
        if hit.get("articulo"):
            cita += f" · Art. {hit['articulo']}"
        partes.append(f"**{i}. {cita}**\n\n> {hit['texto']}\n")

    partes.append("\n" + LEGAL_DISCLAIMER)
    return "\n".join(partes)
