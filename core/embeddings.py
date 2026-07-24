"""Carga perezosa del modelo de embeddings.

El modelo de sentence-transformers se carga una sola vez (es costoso) y se
reutiliza en cada llamada. Se importa dentro de la función para no ralentizar
el arranque de las apps hasta que realmente se necesite.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from .config import EMBED_MODEL


@lru_cache(maxsize=1)
def get_model():
    """Devuelve la instancia (cacheada) del modelo de embeddings."""
    # Import diferido: solo se carga sentence-transformers cuando hace falta.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Genera embeddings para una lista de textos (fragmentos de documento)."""
    model = get_model()
    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return vectors.tolist()


def embed_query(text: str) -> List[float]:
    """Genera el embedding de una consulta individual."""
    return embed_texts([text])[0]
