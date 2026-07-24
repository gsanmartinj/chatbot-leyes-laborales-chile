"""App de chat (Streamlit) — Leyes laborales de Chile.

Interfaz pública de solo consulta. Las personas escriben su pregunta y el
asistente devuelve los fragmentos más relevantes de los PDF cargados por el
administrador, citando documento y página.

Ejecutar:
    streamlit run app_streamlit.py
"""

from __future__ import annotations

import streamlit as st

from core.config import LEGAL_DISCLAIMER
from core.ingest import stats
from core.search import format_answer, search

st.set_page_config(
    page_title="Asistente Laboral Chile",
    page_icon="⚖️",
    layout="centered",
)

# --- Encabezado ---------------------------------------------------------------
st.title("⚖️ Asistente de Leyes Laborales de Chile")
st.caption(
    "Haz preguntas sobre derecho laboral chileno. Las respuestas se basan "
    "únicamente en los documentos cargados en la base de datos."
)

# Estado de la base de datos.
try:
    base = stats()
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo abrir la base de datos: {exc}")
    st.stop()

if base["documentos"] == 0:
    st.warning(
        "La base de datos está vacía. Pide al administrador que suba documentos "
        "PDF desde el panel de administración (Gradio) antes de consultar."
    )
else:
    st.info(
        f"📚 Base de datos: {base['documentos']} documento(s) · "
        f"{base['fragmentos']} fragmento(s) indexado(s)."
    )

# --- Historial de conversación ------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "¡Hola! 👋 Soy un asistente de consulta sobre leyes laborales de "
                "Chile. Pregúntame, por ejemplo, sobre vacaciones, finiquitos, "
                "jornada laboral, licencias o indemnizaciones.\n\n" + LEGAL_DISCLAIMER
            ),
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Entrada del usuario ------------------------------------------------------
pregunta = st.chat_input("Escribe tu pregunta sobre leyes laborales…")

if pregunta:
    st.session_state.messages.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        if base["documentos"] == 0:
            respuesta = (
                "Todavía no hay documentos cargados en la base de datos, así que "
                "no puedo responder. Pide al administrador que suba PDF."
            )
        else:
            with st.spinner("Buscando en los documentos…"):
                hits = search(pregunta)
                respuesta = format_answer(hits)
        st.markdown(respuesta)

    st.session_state.messages.append({"role": "assistant", "content": respuesta})

# --- Barra lateral ------------------------------------------------------------
with st.sidebar:
    st.header("ℹ️ Acerca de")
    st.markdown(
        "Este asistente **no usa IA en la nube**. Funciona con búsqueda "
        "semántica local sobre los PDF cargados y **cita la fuente** de cada "
        "respuesta (documento y página).\n\n"
        "No genera texto nuevo: solo muestra lo que está escrito en los "
        "documentos oficiales que cargó el administrador."
    )
    if st.button("🗑️ Limpiar conversación"):
        st.session_state.messages = st.session_state.messages[:1]
        st.rerun()
