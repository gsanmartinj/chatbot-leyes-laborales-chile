"""Núcleo compartido del chatbot de leyes laborales de Chile.

Contiene la configuración, el acceso a la base vectorial (ChromaDB),
el modelo de embeddings, la ingesta de PDF y la búsqueda semántica.
Tanto la app de chat (Streamlit) como el panel de administración (Gradio)
importan desde aquí para compartir la misma base de datos.
"""
