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
import unicodedata
from pathlib import Path
from typing import Dict, List

from .articles import detect_article
from .config import LEGAL_DISCLAIMER, MAX_ARTICLE_CHUNKS, MIN_SCORE, TOP_K
from .db import get_collection
from .embeddings import embed_query

# Reexportado: `detect_article` vivía aquí antes de mudarse a core.articles.
__all__ = ["detect_article", "search", "answer", "format_answer"]


def _plegar(texto: str) -> str:
    """Minúsculas, sin tildes y sin puntuación: para comparar nombres de documento."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes.lower()).strip()


def _elegir_fuente(article: str, question: str, fuentes: List[str]) -> str:
    """Decide de qué documento mostrar el artículo pedido.

    Cada cuerpo legal del corpus tiene su propio "artículo 5", así que hay que
    quedarse con uno. Primero se mira si la pregunta nombra el documento
    ("art. 5 del Código del Trabajo"); si no, se deja que la base decida cuál de
    las versiones de ese artículo se parece más a la pregunta.
    """
    if len(fuentes) == 1:
        return fuentes[0]

    # 1) ¿La pregunta nombra uno de los documentos indexados? Se exige que el
    #    nombre calce como palabra completa: con `in` a secas, un documento
    #    llamado "1.pdf" se daría por nombrado en "artículo 51".
    pregunta = _plegar(question)
    nombrados = [
        f for f in fuentes
        if (nombre := _plegar(Path(f).stem))
        and re.search(rf"\b{re.escape(nombre)}\b", pregunta)
    ]
    if len(nombrados) == 1:
        return nombrados[0]
    candidatas = nombrados or fuentes

    # 2) Si no, el documento cuya versión del artículo es más afín a la pregunta.
    #    Una sola consulta acotada al artículo: no hay que reembeber nada.
    resultado = get_collection().query(
        query_embeddings=[embed_query(question)],
        n_results=1,
        where={"articulo": article},
        include=["metadatas"],
    )
    metas = (resultado.get("metadatas") or [[]])[0]
    if metas:
        mejor = str((metas[0] or {}).get("source", ""))
        if mejor in candidatas:
            return mejor
    return sorted(candidatas)[0]


def _search_by_article(article: str, question: str) -> List[Dict[str, object]]:
    """Recupera los fragmentos de un artículo, acotados a un solo documento.

    `article` es la etiqueta canónica ("157", "157 bis"), no un número: la
    coincidencia es exacta, de modo que preguntar por el 157 no arrastra el
    texto del 157 bis, que es un artículo distinto.

    Devolver las coincidencias de todos los documentos mezclaba textos de leyes
    distintas bajo una misma respuesta, y el recorte final por MAX_ARTICLE_CHUNKS
    podía dejar fuera documentos enteros sin avisar.
    """
    collection = get_collection()
    got = collection.get(
        where={"articulo": article}, include=["documents", "metadatas"]
    )
    docs = got.get("documents") or []
    metas = got.get("metadatas") or []

    # Agrupar por documento de origen.
    por_fuente: Dict[str, List[Dict[str, object]]] = {}
    for text, meta in zip(docs, metas):
        meta = meta or {}
        fuente = str(meta.get("source", "desconocido"))
        por_fuente.setdefault(fuente, []).append(
            {
                "texto": text,
                "source": fuente,
                "page": meta.get("page", "?"),
                "articulo": meta.get("articulo"),
                "seq": meta.get("seq", 0),
                "score": 1.0,
            }
        )
    if not por_fuente:
        return []

    elegida = _elegir_fuente(article, question, list(por_fuente))
    # Ordenar por su posición original en el documento.
    hits = sorted(por_fuente[elegida], key=lambda h: h.get("seq", 0))
    hits = hits[:MAX_ARTICLE_CHUNKS]

    # Dejar constancia de los otros cuerpos legales que también tienen ese
    # artículo, para que la respuesta pueda ofrecerlos en vez de ocultarlos.
    otras = sorted(f for f in por_fuente if f != elegida)
    if otras and hits:
        hits[0]["otras_fuentes"] = otras
    return hits


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


def search(
    question: str, top_k: int = TOP_K, modo_articulo: bool = True
) -> List[Dict[str, object]]:
    """Busca los fragmentos más relevantes para la pregunta (modo híbrido).

    Args:
        question: texto de la consulta.
        top_k: fragmentos a devolver en la búsqueda semántica.
        modo_articulo: si es False, se salta el atajo por artículo y va siempre
            por similitud. Lo usa la revisión de contratos: una cláusula es un
            texto largo que puede citar un artículo de pasada, y quedarse solo
            con ese artículo descartaría el resto de la normativa pertinente.

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
    article = detect_article(question) if modo_articulo else None
    if article is not None:
        hits = _search_by_article(article, question)
        if hits:
            return hits
        # Ese artículo no está en el corpus. Se responde por similitud, pero
        # queda constancia: caer en silencio hace creer a quien pregunta que
        # está leyendo el artículo que pidió, y aquí eso es una cita falsa.
        hits = _search_semantic(question, top_k)
        if hits:
            hits[0]["articulo_no_hallado"] = article
        return hits

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
            texto = (
                articulo_no_hallado_md(hits)
                + generate_answer(question, hits)
                + otras_fuentes_md(hits)
            )
            return {"text": texto, "hits": hits, "mode": "llm"}
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

    partes = [articulo_no_hallado_md(hits)]
    partes.append("Esto es lo que encontré en los documentos cargados:\n")
    for i, hit in enumerate(hits, start=1):
        cita = f"*{hit['source']}* — pág. {hit['page']}"
        if hit.get("articulo"):
            cita += f" · Art. {hit['articulo']}"
        partes.append(f"**{i}. {cita}**\n\n> {hit['texto']}\n")

    partes.append(otras_fuentes_md(hits))
    partes.append("\n" + LEGAL_DISCLAIMER)
    return "\n".join(p for p in partes if p)


def articulo_no_hallado_md(hits: List[Dict[str, object]]) -> str:
    """Aviso de que el artículo pedido no está en el corpus.

    Lo que sigue son resultados por similitud, no el artículo solicitado. Sin
    este aviso la respuesta parece contestar la pregunta literal.
    """
    pedido = hits[0].get("articulo_no_hallado") if hits else None
    if not pedido:
        return ""
    return (
        f"*No encontré el artículo {pedido} en los documentos cargados. Le "
        "muestro lo más relacionado que hay; puede que ese artículo esté en un "
        "cuerpo legal que aún no se ha subido.*\n\n"
    )


def otras_fuentes_md(hits: List[Dict[str, object]]) -> str:
    """Aviso de que el artículo consultado también existe en otros documentos.

    La búsqueda por artículo se queda con un solo cuerpo legal; esto le dice a la
    persona dónde más mirar, para que la elección no pase inadvertida.
    """
    otras = hits[0].get("otras_fuentes") if hits else None
    if not otras:
        return ""
    articulo = hits[0].get("articulo")
    return (
        f"\nEse mismo artículo ({articulo}) también aparece en: "
        + ", ".join(f"*{f}*" for f in otras)
        + ". Nómbrelo en su pregunta si se refería a alguno de ellos.\n"
    )
