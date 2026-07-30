# ⚖️ Chatbot de Leyes Laborales de Chile

Asistente web para consultar sobre **derecho laboral chileno**. Funciona con una
**base de datos vectorial local** que se alimenta subiendo PDF (Código del Trabajo,
leyes, dictámenes, etc.). El asistente responde recuperando los fragmentos más
relevantes de esos documentos y **cita la fuente** (archivo y página).

- ✅ **Respuestas ancladas al corpus** — solo se responde con lo que está en los PDF
  cargados, y cada respuesta cita archivo, página y artículo.
- ✅ **Funciona sin conexión** — la búsqueda (embeddings + ChromaDB) corre entera en
  este equipo, sin costo por consulta.
- ⚠️ **La redacción es opcional y sí sale del equipo.** Si configuras un proveedor
  (DeepSeek o Gemini), tu pregunta y los fragmentos recuperados se envían a sus
  servidores. Sin proveedor configurado, nada sale del equipo. Ver
  [Respuestas redactadas por un modelo](#opcional-respuestas-redactadas-por-un-modelo).

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
core/             # lógica: config, db, embeddings, artículos, ingesta, búsqueda, LLM
ui/               # capa visual: CSS y componentes de cada app
tests/            # pruebas del detector de artículos y de la revisión
app_streamlit.py  # chat (usuarios)
app_gradio.py     # panel admin (subir PDF)
.streamlit/       # tema base de Streamlit
data/pdfs/        # copia de los PDF cargados
data/chroma/      # base vectorial persistente
```

### Cómo se identifican los artículos

`core/articles.py` etiqueta cada fragmento con el artículo al que pertenece; es lo
que permite responder «¿qué dice el artículo 22?» con una cita exacta en vez de
una aproximación semántica. El texto legal chileno impone tres distinciones que
ese módulo trata explícitamente:

- **Encabezado vs. remisión.** «Art. 5. … conforme a los arts. 22 y 23» contiene
  un solo artículo, el 5.
- **El salto de línea de un PDF no cierra la frase.** El PDF corta los renglones a
  mitad de oración, así que una remisión puede quedar abriendo renglón sin abrir
  artículo. Se mira cómo termina la línea anterior, no solo el carácter previo.
- **`157`, `157 bis` y `157 quinquies` son artículos distintos.** La etiqueta es
  `"157 bis"`, no `157`: colapsarlos mezcla textos ajenos bajo una misma cita.
  También se aceptan las dos formas del ordinal, `1º` y `1°`, que son caracteres
  Unicode distintos.

`DETECTOR_VERSION` en ese módulo se guarda con cada fragmento. Si las reglas
cambian, los documentos indexados con la versión anterior aparecen marcados como
desactualizados y ambas apps lo avisan: sus etiquetas ya no son las que produce
el código, así que la búsqueda por artículo respondería sobre datos obsoletos.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

Cubren el detector de artículos (con casos tomados de PDF reales de leychile.cl)
y el filtro que descarta hallazgos que el modelo no puede fundamentar en un
fragmento entregado.

**Diseño.** Dirección editorial jurídica: papel cálido con grano, tipografías
Fraunces (títulos) y Newsreader (prosa), acento bordeaux. El chat va en claro y
el panel de administración en oscuro, para distinguir la cara pública de la
trastienda. Las fuentes se cargan desde Google Fonts.

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

Abre la URL que aparece (por defecto http://127.0.0.1:7860). El navegador pedirá
usuario y contraseña (`ADMIN_USER` / `ADMIN_PASSWORD` del `.env`; por defecto el
usuario es `admin`). Una vez dentro, en la pestaña **"Cargar documentos"**
selecciona uno o más PDF e **Indexar**.

> La autenticación la aplica el propio servidor de Gradio: sin sesión válida no
> se puede llamar a los endpoints de carga ni de borrado.

En **"Documentos indexados"**, la columna *Etiquetado* indica si cada documento
está al día con las reglas vigentes de detección de artículos. Los que digan
**Reindexar** se corrigen con el botón **«Reindexar desactualizados»**, que los
reprocesa desde la copia guardada en `data/pdfs/` sin volver a subirlos.

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

## Revisión de contratos

La app de chat tiene una segunda pestaña, **«Revisar contrato»**: se sube un
contrato en PDF, Word o pegando el texto, y se obtienen los problemas detectados
con su recomendación, ordenados por gravedad y con el fundamento normativo.

- **El contrato no se guarda ni se indexa.** Se procesa en memoria y se descarta:
  contiene datos personales y contaminaría el corpus normativo.
- ⚠️ **Pero su texto completo sí se envía al proveedor del modelo** (DeepSeek o
  Gemini) para el análisis, con los datos personales que contenga: nombre, RUT y
  remuneración. No queda en este equipo ni en la base, pero sale de él. La app lo
  advierte antes de subir el archivo; si le preocupa, anonimice esos datos primero.
- **Modo estricto.** Solo se reportan problemas respaldados por los PDF cargados.
  Los hallazgos que el modelo no logra fundamentar en un documento real de la
  base **se descartan automáticamente** y se informa cuántos fueron.
- Por eso **la calidad depende del corpus**: con pocos documentos se detectará
  poco. Cargue el Código del Trabajo para una revisión completa.
- Requiere un modelo configurado (ver la sección siguiente): la búsqueda por sí
  sola no puede evaluar un contrato.
- El informe puede descargarse en Markdown.

## (Opcional) Respuestas redactadas por un modelo

Por defecto el chat muestra los **fragmentos** relevantes de los PDF. Si prefieres
que un modelo **redacte** una respuesta en lenguaje natural (basada solo en esos
fragmentos), configura un proveedor en `.env`.

**Opción A — DeepSeek V4 Pro** (u otro endpoint compatible con OpenAI).
Clave en https://build.nvidia.com:
```
LLM_API_KEY=tu_clave_aqui
LLM_BASE_URL=https://integrate.api.nvidia.com/v1
LLM_MODEL=deepseek-ai/deepseek-v4-pro
```

**Opción B — Gemini.** Clave gratuita en https://aistudio.google.com/apikey:
```
GEMINI_API_KEY=tu_clave_aqui
```

Con `LLM_PROVIDER=auto` (por defecto) se usa DeepSeek si hay `LLM_API_KEY`; si no,
Gemini; si no hay ninguna, modo local.

Cómo funciona: la **búsqueda sigue siendo local**; solo los fragmentos recuperados
y tu pregunta se envían al proveedor, que redacta la respuesta citando las fuentes.

- Sin proveedor configurado, la app funciona 100% local (no sale nada del equipo).
- Si la llamada falla, se reintenta hasta 3 veces y, si aun así falla, el chat
  vuelve automáticamente al modo local mostrando los fragmentos.
- Nunca escribas la clave en el código: va en `.env`, que está en `.gitignore`.
- ⚠️ Con un proveedor activo, tus textos y preguntas salen hacia sus servidores.

## Notas y limitaciones

- **Concurrencia:** pensado para uso local de baja concurrencia. ChromaDB usa SQLite;
  para muchos usuarios simultáneos convendría migrar a Chroma en modo servidor.
- **No es asesoría legal.** La información es orientativa; cada respuesta incluye un
  aviso recordándolo.
- Para reindexar un documento, simplemente vuelve a subirlo con el mismo nombre:
  reemplaza la versión anterior. Si solo cambió el detector de artículos, basta el
  botón **«Reindexar desactualizados»**.
- **Leyes modificatorias.** Una ley que modifica otro cuerpo legal (p. ej. la Ley
  21.690 sobre el Código del Trabajo) cita e intercala artículos ajenos. Los
  artículos que **inserta** se indexan correctamente, pero conviene cargar también
  el texto refundido del Código: preguntar por un artículo cuya versión vigente no
  está en el corpus devolverá el de la ley modificatoria, avisando de ello.
- Si se pregunta por un artículo que no está indexado, la respuesta lo dice
  expresamente y ofrece lo más cercano por similitud, en vez de aparentar que
  responde a la pregunta literal.
