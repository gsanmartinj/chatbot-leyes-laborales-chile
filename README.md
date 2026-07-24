# ⚖️ Chatbot de Leyes Laborales de Chile

Asistente web para consultar sobre **derecho laboral chileno**. Funciona con una
**base de datos vectorial local** que se alimenta subiendo PDF (Código del Trabajo,
leyes, dictámenes, etc.). El asistente responde recuperando los fragmentos más
relevantes de esos documentos y **cita la fuente** (archivo y página).

- ✅ **100 % local y privado** — no usa la API de Claude ni ningún servicio en la nube.
- ✅ **Sin alucinaciones** — solo muestra texto que está en los documentos oficiales.
- ✅ **Sin costo por consulta.**

## Arquitectura

Dos aplicaciones que comparten la misma base de datos:

| App | Herramienta | Para quién | Función |
|-----|-------------|-----------|---------|
| **Chat** | Streamlit | Usuarios | Hacer preguntas y ver respuestas con citas. |
| **Admin** | Gradio | Administrador | Subir / listar / eliminar PDF (con contraseña). |

Bajo el capó:
- **pypdf** extrae el texto de cada página.
- El texto se divide en fragmentos y se convierte en vectores con
  **sentence-transformers** (modelo multilingüe, corre offline).
- Los vectores se guardan en **ChromaDB** (`data/chroma/`).
- Al preguntar, la consulta se vectoriza y se recuperan los fragmentos más cercanos.

```
core/           # lógica compartida (config, db, embeddings, ingesta, búsqueda)
app_streamlit.py  # chat (usuarios)
app_gradio.py     # panel admin (subir PDF)
data/pdfs/      # copia de los PDF cargados
data/chroma/    # base vectorial persistente
```

## Instalación

Requiere **Python 3.9+**.

```bash
# 1. (Recomendado) crear un entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# source .venv/bin/activate     # Linux / macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar la contraseña de administrador
copy .env.example .env          # Windows
# cp .env.example .env            # Linux / macOS
# …luego edita .env y cambia ADMIN_PASSWORD
```

> La primera vez que se use, se descargará el modelo de embeddings (~120 MB) desde
> HuggingFace. Después funciona sin conexión.

## Uso

### 1) Cargar documentos (panel admin, Gradio)

```bash
python app_gradio.py
```

Abre la URL que aparece (por defecto http://127.0.0.1:7860), ingresa la contraseña,
y en la pestaña **"Subir documentos"** selecciona uno o más PDF e **Indexar**.

### 2) Consultar (chat, Streamlit)

```bash
streamlit run app_streamlit.py
```

Abre http://localhost:8501 y escribe tu pregunta (ej. *"¿Cuántos días de vacaciones
me corresponden al año?"*). El asistente mostrará los fragmentos relevantes con su cita.

> Puedes tener **ambas apps corriendo a la vez** (en dos terminales). Comparten la
> misma base de datos: lo que subes en Gradio queda disponible al instante en el chat.

## ¿De dónde saco los PDF?

Fuentes oficiales chilenas (documentos públicos):
- **Código del Trabajo** — Biblioteca del Congreso Nacional (BCN), [leychile.cl](https://www.leychile.cl).
- **Dirección del Trabajo** — dictámenes y guías, [dt.gob.cl](https://www.dt.gob.cl).

> Usa PDF con **texto seleccionable**. Los PDF escaneados (solo imagen) no tienen
> texto extraíble; requerirían OCR previo.

## Notas y limitaciones

- **Concurrencia:** pensado para uso local de baja concurrencia. ChromaDB usa SQLite;
  para muchos usuarios simultáneos convendría migrar a Chroma en modo servidor.
- **No es asesoría legal.** La información es orientativa; cada respuesta incluye un
  aviso recordándolo.
- Para reindexar un documento, simplemente vuelve a subirlo con el mismo nombre:
  reemplaza la versión anterior.
