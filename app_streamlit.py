"""App de chat (Streamlit) — Leyes laborales de Chile.

Interfaz pública de solo consulta. Las personas escriben su pregunta y el
asistente responde a partir de los PDF cargados por el administrador, citando
documento, página y artículo.

Ejecutar:
    streamlit run app_streamlit.py
"""

from __future__ import annotations

import streamlit as st

from core.config import LEGAL_DISCLAIMER
from core.ingest import stats
from core.llm import gemini_available
from core.search import answer
from ui.streamlit_ui import CSS, SUGGESTIONS, header_html, strip_html, warn_html

st.set_page_config(
    page_title="Derechos Laborales · Chile",
    page_icon="§",
    layout="centered",
)
st.markdown(CSS, unsafe_allow_html=True)

BIENVENIDA = (
    "Bienvenido. Puede consultarme sobre vacaciones, jornada de trabajo, "
    "despidos, finiquitos, licencias o cualquier materia contenida en los "
    "documentos cargados.\n\n"
    "Escriba su pregunta en lenguaje cotidiano: no necesita conocer términos "
    "legales.\n\n" + LEGAL_DISCLAIMER
)


def _sources_md(hits) -> str:
    """Lista compacta de fuentes para adjuntar bajo una respuesta redactada."""
    if not hits:
        return ""
    lineas = ["\n\n---\n**Fuentes consultadas**\n"]
    for h in hits:
        cita = f"- *{h['source']}* — pág. {h['page']}"
        if h.get("articulo"):
            cita += f" · Art. {h['articulo']}"
        lineas.append(cita)
    return "\n".join(lineas)


# --- Cabecera -----------------------------------------------------------------
st.markdown(header_html(), unsafe_allow_html=True)

try:
    base = stats()
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo abrir la base de datos: {exc}")
    st.stop()

usa_gemini = gemini_available()
st.markdown(
    strip_html(
        base["documentos"],
        base["fragmentos"],
        "Gemini" if usa_gemini else "Local",
    ),
    unsafe_allow_html=True,
)

if base["documentos"] == 0:
    st.markdown(
        warn_html(
            "La base de datos está vacía. Solicite al administrador que cargue "
            "los documentos desde el panel de administración antes de consultar."
        ),
        unsafe_allow_html=True,
    )

# --- Historial ----------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": BIENVENIDA}]

# Preguntas sugeridas: solo al inicio, como punto de partida.
if len(st.session_state.messages) == 1 and base["documentos"] > 0:
    st.markdown('<p class="lex-hint">Para comenzar</p>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, sug in enumerate(SUGGESTIONS):
        if cols[i % 2].button(sug, key=f"sug_{i}", use_container_width=True):
            st.session_state.pendiente = sug
            st.rerun()

for msg in st.session_state.messages:
    # El glifo del avatar (§ / ◆) se dibuja por CSS: Streamlit solo admite
    # emojis o imágenes en `avatar`.
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Entrada ------------------------------------------------------------------
pregunta = st.chat_input("Escriba su consulta…") or st.session_state.pop(
    "pendiente", None
)

if pregunta:
    st.session_state.messages.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        if base["documentos"] == 0:
            respuesta = (
                "Aún no hay documentos cargados en la base de datos, por lo que "
                "no puedo responder su consulta."
            )
        else:
            spinner = "Redactando respuesta" if usa_gemini else "Buscando en los documentos"
            with st.spinner(spinner):
                res = answer(pregunta)
                respuesta = res["text"]
                if res["mode"] in ("gemini", "local-fallback"):
                    respuesta += _sources_md(res["hits"])
        st.markdown(respuesta)

    st.session_state.messages.append({"role": "assistant", "content": respuesta})

# --- Barra lateral ------------------------------------------------------------
with st.sidebar:
    st.markdown('<p class="lex-side-t">Cómo funciona</p>', unsafe_allow_html=True)
    if usa_gemini:
        st.markdown(
            "**Motor:** Gemini (redacción) sobre búsqueda semántica local.\n\n"
            "La búsqueda de los fragmentos ocurre en este equipo. Luego **Gemini "
            "redacta** la respuesta usando únicamente esos fragmentos y cita la "
            "fuente. Su pregunta y los textos recuperados se envían a Google."
        )
    else:
        st.markdown(
            "**Motor:** local, sin servicios en la nube.\n\n"
            "Búsqueda semántica sobre los documentos cargados. Se muestran los "
            "fragmentos pertinentes con su fuente; no se genera texto nuevo.\n\n"
            "_Para obtener respuestas redactadas, configure una `GEMINI_API_KEY` "
            "en el archivo `.env`._"
        )

    st.markdown("---")
    st.markdown('<p class="lex-side-t">Advertencia</p>', unsafe_allow_html=True)
    st.markdown(
        "Este asistente **no es un servicio oficial** ni sustituye la asesoría de "
        "un abogado. Para casos particulares, consulte a la **Dirección del "
        "Trabajo**."
    )

    st.markdown("---")
    if st.button("Reiniciar conversación", use_container_width=True):
        st.session_state.messages = st.session_state.messages[:1]
        st.rerun()
