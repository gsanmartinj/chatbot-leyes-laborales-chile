"""Ingesta de PDF a la base vectorial.

Flujo: PDF -> texto por página -> fragmentos (chunks) con solapamiento ->
embeddings -> almacenamiento en ChromaDB con metadatos para poder citar
(archivo de origen y número de página).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict, List

from .config import CHUNK_OVERLAP, CHUNK_SIZE, PDF_DIR
from .db import get_collection
from .embeddings import embed_texts


# Palabras ordinales usadas en la numeración de artículos ("Artículo primero").
_ORDINALS = {
    "primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5,
    "sexto": 6, "septimo": 7, "séptimo": 7, "octavo": 8, "noveno": 9,
    "decimo": 10, "décimo": 10, "undecimo": 11, "undécimo": 11,
    "duodecimo": 12, "duodécimo": 12, "unico": 1, "único": 1,
}

# Detecta encabezados de artículo: "Artículo 1", "Art. 12", "Artículo primero".
_ART_RE = re.compile(
    r"\bart[íi]culo?s?\.?\s+(\d{1,4}|"
    + "|".join(_ORDINALS.keys())
    + r")\b",
    re.IGNORECASE,
)


def _article_number(token: str) -> int | None:
    """Convierte el token capturado ('12' o 'primero') a un número de artículo."""
    token = token.lower()
    if token.isdigit():
        return int(token)
    return _ORDINALS.get(token)


def _clean(text: str) -> str:
    """Normaliza espacios en blanco del texto extraído del PDF."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Divide un texto en fragmentos de ~`size` caracteres con `overlap` de solapamiento.

    Intenta cortar en un límite de palabra para no partir términos por la mitad.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        # Retroceder hasta un espacio cercano para no cortar una palabra.
        if end < n:
            space = text.rfind(" ", start + size - overlap, end)
            if space != -1 and space > start:
                end = space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _extract_pages(pdf_path: Path) -> List[str]:
    """Extrae el texto de cada página del PDF (índice 0 = página 1)."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return [_clean(page.extract_text() or "") for page in reader.pages]


def ingest_pdf(pdf_path: str | Path, source_name: str | None = None) -> Dict[str, int]:
    """Indexa un PDF en la base vectorial.

    Args:
        pdf_path: ruta al PDF a procesar.
        source_name: nombre con el que se guardará/citará. Por defecto, el nombre del archivo.

    Returns:
        dict con {"chunks": n_fragmentos, "pages": n_paginas}.
    """
    pdf_path = Path(pdf_path)
    source = source_name or pdf_path.name

    # Si ya existía un documento con ese nombre, lo reemplazamos (re-indexación limpia).
    delete_document(source, remove_file=False)

    pages = _extract_pages(pdf_path)

    documents: List[str] = []
    metadatas: List[Dict[str, object]] = []
    ids: List[str] = []

    current_article: int | None = None  # último artículo visto (se arrastra entre páginas)
    seq = 0                              # orden global del fragmento (para reordenar luego)

    for page_num, page_text in enumerate(pages, start=1):
        # Posiciones y números de los encabezados de artículo en esta página.
        markers = [
            (m.start(), _article_number(m.group(1)))
            for m in _ART_RE.finditer(page_text)
        ]
        markers = [(pos, num) for pos, num in markers if num is not None]

        cursor = 0
        for chunk_idx, chunk in enumerate(_chunk_text(page_text)):
            # Localizar el fragmento dentro de la página para saber su artículo.
            idx = page_text.find(chunk, cursor)
            start = idx if idx != -1 else cursor
            cursor = start + len(chunk)

            # Artículo activo al inicio del fragmento (arrastrando el anterior).
            article = current_article
            for pos, num in markers:
                if pos <= start:
                    article = num
                else:
                    break

            meta: Dict[str, object] = {"source": source, "page": page_num, "seq": seq}
            if article is not None:
                meta["articulo"] = article

            documents.append(chunk)
            metadatas.append(meta)
            ids.append(f"{source}::p{page_num}::c{chunk_idx}")
            seq += 1

            # Arrastrar el último artículo que aparece dentro de este fragmento.
            for pos, num in markers:
                if pos < cursor:
                    current_article = num

        if markers:
            current_article = markers[-1][1]

    if not documents:
        raise ValueError(
            "No se pudo extraer texto de este PDF. "
            "Puede ser un documento escaneado (imagen) sin texto seleccionable."
        )

    # Guardar una copia del PDF original en data/pdfs/.
    dest = PDF_DIR / source
    if pdf_path.resolve() != dest.resolve():
        shutil.copy2(pdf_path, dest)

    # Calcular embeddings e insertar en lotes para no saturar memoria.
    collection = get_collection()
    batch = 128
    for i in range(0, len(documents), batch):
        docs_b = documents[i : i + batch]
        collection.add(
            ids=ids[i : i + batch],
            documents=docs_b,
            metadatas=metadatas[i : i + batch],
            embeddings=embed_texts(docs_b),
        )

    return {"chunks": len(documents), "pages": len(pages)}


def list_documents() -> List[Dict[str, object]]:
    """Lista los documentos indexados con su número de fragmentos.

    Returns:
        lista de dicts {"source": nombre, "chunks": n} ordenada por nombre.
    """
    collection = get_collection()
    got = collection.get(include=["metadatas"])
    counts: Dict[str, int] = {}
    for meta in got.get("metadatas") or []:
        src = str(meta.get("source", "desconocido"))
        counts[src] = counts.get(src, 0) + 1
    return [
        {"source": src, "chunks": counts[src]} for src in sorted(counts)
    ]


def delete_document(source: str, remove_file: bool = True) -> None:
    """Elimina de la base todos los fragmentos de un documento y (opcional) su PDF."""
    collection = get_collection()
    collection.delete(where={"source": source})
    if remove_file:
        pdf_file = PDF_DIR / source
        if pdf_file.exists():
            pdf_file.unlink()


def stats() -> Dict[str, int]:
    """Devuelve estadísticas globales de la base: nº de documentos y de fragmentos."""
    docs = list_documents()
    return {
        "documentos": len(docs),
        "fragmentos": sum(int(d["chunks"]) for d in docs),
    }
