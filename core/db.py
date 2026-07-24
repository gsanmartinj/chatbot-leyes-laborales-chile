"""Acceso a la base vectorial ChromaDB (persistente y compartida).

Ambas apps abren la misma carpeta CHROMA_DIR, por lo que comparten los datos.
Usamos un cliente cacheado por proceso para no reabrir la conexión en cada llamada.
"""

from __future__ import annotations

from functools import lru_cache

from .config import CHROMA_DIR, COLLECTION_NAME


@lru_cache(maxsize=1)
def get_client():
    """Cliente persistente de ChromaDB (uno por proceso)."""
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )


def get_collection():
    """Devuelve (creando si no existe) la colección de fragmentos.

    Usamos distancia coseno; los embeddings ya vienen normalizados.
    """
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
