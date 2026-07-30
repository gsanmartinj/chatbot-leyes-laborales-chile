"""App de chat (Streamlit) — Leyes laborales de Chile.

Dos secciones:
- **Consultar**: preguntas libres respondidas con los PDF cargados.
- **Revisar contrato**: se sube un contrato, se detectan problemas y se dan
  recomendaciones fundamentadas en esos mismos PDF. El contrato se analiza en
  memoria y se descarta: nunca se indexa ni se guarda.

Ejecutar:
    streamlit run app_streamlit.py
"""

from __future__ import annotations

import streamlit as st

from core.config import LEGAL_DISCLAIMER
from core.contract import extract_text, report_markdown, review_contract
from core.ingest import stats
from core.llm import llm_available, provider_label
from core.search import answer
from ui.streamlit_ui import (
    CSS,
    SUGGESTIONS,
    finding_html,
    header_html,
    note_html,
    ok_html,
    strip_html,
    summary_html,
    warn_html,
)

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

usa_llm = llm_available()
motor = provider_label()
st.markdown(
    strip_html(base["documentos"], base["fragmentos"], motor),
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

tab_consulta, tab_contrato = st.tabs(["Consultar", "Revisar contrato"])

# =============================================================================
# Pestaña 1 · Consultar
# =============================================================================
with tab_consulta:
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
                    "Aún no hay documentos cargados en la base de datos, por lo "
                    "que no puedo responder su consulta."
                )
            else:
                spinner = (
                    "Redactando respuesta" if usa_llm else "Buscando en los documentos"
                )
                with st.spinner(spinner):
                    res = answer(pregunta)
                    respuesta = res["text"]
                    if res["mode"] in ("llm", "local-fallback"):
                        respuesta += _sources_md(res["hits"])
            st.markdown(respuesta)

        st.session_state.messages.append({"role": "assistant", "content": respuesta})

# =============================================================================
# Pestaña 2 · Revisar contrato
# =============================================================================
with tab_contrato:
    st.markdown(
        note_html(
            "Suba su contrato de trabajo y se revisará <b>contra los documentos "
            "cargados en el sistema</b>. Solo se señalan problemas respaldados por "
            "esa normativa. El contrato se analiza en memoria y <b>no se guarda "
            "ni se incorpora a la base de datos</b>."
        ),
        unsafe_allow_html=True,
    )

    if not usa_llm:
        st.markdown(
            warn_html(
                "Esta función requiere un modelo de lenguaje configurado "
                "(<code>LLM_API_KEY</code> en el archivo <code>.env</code>). La "
                "búsqueda por sí sola no puede evaluar un contrato."
            ),
            unsafe_allow_html=True,
        )
    elif base["documentos"] == 0:
        st.markdown(
            warn_html("Cargue documentos en la base antes de revisar un contrato."),
            unsafe_allow_html=True,
        )
    else:
        if base["documentos"] < 2:
            st.markdown(
                warn_html(
                    "La base contiene pocos documentos: la revisión solo detectará "
                    "lo que ellos respalden. Para un análisis completo, cargue el "
                    "Código del Trabajo."
                ),
                unsafe_allow_html=True,
            )

        archivo = st.file_uploader(
            "Contrato en PDF, Word o texto",
            type=["pdf", "docx", "txt"],
            key="contrato_file",
        )
        pegado = st.text_area(
            "…o pegue aquí el texto del contrato",
            height=150,
            key="contrato_texto",
            placeholder="CONTRATO DE TRABAJO\n\nPRIMERO: …",
        )

        if st.button("Analizar contrato", type="primary", key="btn_revisar"):
            try:
                if archivo is not None:
                    texto = extract_text(archivo.getvalue(), archivo.name)
                    nombre = archivo.name
                elif pegado.strip():
                    texto = pegado.strip()
                    nombre = "texto pegado"
                else:
                    texto = nombre = ""
                    st.warning("Suba un archivo o pegue el texto del contrato.")

                if texto:
                    barra = st.progress(0.0, text="Preparando…")

                    def _avance(pct: float, msg: str) -> None:
                        barra.progress(min(max(pct, 0.0), 1.0), text=msg)

                    resultado = review_contract(texto, progress=_avance)
                    barra.empty()
                    st.session_state.revision = {"res": resultado, "nombre": nombre}
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo revisar el contrato: {exc}")

        # --- Resultado (persiste entre recargas) ---------------------------
        revision = st.session_state.get("revision")
        if revision:
            res = revision["res"]
            hallazgos = res["hallazgos"]
            altas = sum(1 for h in hallazgos if h["gravedad"] == "alta")

            st.markdown(
                summary_html(res["clausulas"], altas, len(hallazgos)),
                unsafe_allow_html=True,
            )

            # escapar=True: los avisos pueden llevar el texto de una excepción del
            # proveedor, que no es contenido de confianza.
            for aviso in res.get("avisos", []):
                st.markdown(note_html(aviso, escapar=True), unsafe_allow_html=True)

            if hallazgos:
                for h in hallazgos:
                    st.markdown(finding_html(h), unsafe_allow_html=True)
            else:
                st.markdown(
                    ok_html(
                        "No se detectaron problemas respaldados por los documentos "
                        "cargados. Esto no garantiza que el contrato sea correcto: "
                        "solo significa que la normativa indexada no permite "
                        "objetarlo."
                    ),
                    unsafe_allow_html=True,
                )

            st.download_button(
                "Descargar informe",
                data=report_markdown(res, revision["nombre"]).encode("utf-8"),
                file_name="informe_revision.md",
                mime="text/markdown",
            )

# =============================================================================
# Barra lateral
# =============================================================================
with st.sidebar:
    st.markdown('<p class="lex-side-t">Cómo funciona</p>', unsafe_allow_html=True)
    if usa_llm:
        st.markdown(
            f"**Motor:** {motor} (redacción) sobre búsqueda semántica local.\n\n"
            "La búsqueda de los fragmentos ocurre en este equipo. Luego el modelo "
            "**redacta** la respuesta usando únicamente esos fragmentos y cita la "
            "fuente. Su pregunta y los textos recuperados se envían al proveedor "
            "del modelo."
        )
    else:
        st.markdown(
            "**Motor:** local, sin servicios en la nube.\n\n"
            "Búsqueda semántica sobre los documentos cargados. Se muestran los "
            "fragmentos pertinentes con su fuente; no se genera texto nuevo.\n\n"
            "_Para obtener respuestas redactadas, configure `LLM_API_KEY` en el "
            "archivo `.env`._"
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
