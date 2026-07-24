"""Búsqueda semántica sobre la base vectorial.

Convierte la pregunta del usuario en un embedding, recupera los fragmentos más
cercanos en ChromaDB y los devuelve con sus metadatos de cita (archivo y página).
No genera texto nuevo: solo recupera y presenta lo que está en los documentos.
"""

from __future__ import annotations

from typing import Dict, List

from .config import LEGAL_DISCLAIMER, TOP_K
from .db import get_collection
from .embeddings import embed_query


def search(question: str, top_k: int = TOP_K) -> List[Dict[str, object]]:
    """Devuelve los fragmentos más relevantes para la pregunta.

    Returns:
        lista de dicts {"texto", "source", "page", "score"} ordenada por relevancia.
        `score` va de 0 a 1 (1 = más relevante).
    """
    question = (question or "").strip()
    if not question:
        return []

    collection = get_collection()
    if collection.count() == 0:
        return []

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
        # Distancia coseno (0 = idéntico). La convertimos a un score legible 0-1.
        score = max(0.0, 1.0 - float(dist))
        hits.append(
            {
                "texto": text,
                "source": meta.get("source", "desconocido"),
                "page": meta.get("page", "?"),
                "score": round(score, 3),
            }
        )
    return hits


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
        cita = f"📄 *{hit['source']}* — pág. {hit['page']}"
        partes.append(f"**{i}. {cita}**\n\n> {hit['texto']}\n")

    partes.append("\n" + LEGAL_DISCLAIMER)
    return "\n".join(partes)
