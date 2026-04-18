import os
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq

# 1. Configuración de la página
st.set_page_config(page_title="Chatbot RRHH PUCP", page_icon="🤖", layout="centered")

# 2. Inicializar conexión a Firebase
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        # Aquí lee el TOML que guardamos en st.secrets
        cred_dict = dict(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# 3. Inicializar conexión a Groq
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("Falta GROQ_API_KEY en st.secrets.")
    st.stop()
client = Groq(api_key=GROQ_API_KEY)

# 4. Lógica de Autenticación (Login con DNI)
st.title("🤖 Asistente de RRHH - PUCP")

# Estado de la sesión para guardar los datos del usuario logueado
if "user_data" not in st.session_state:
    st.session_state.user_data = None

# Pantalla de Login
if st.session_state.user_data is None:
    st.write("Por favor, ingresa tu número de documento para acceder.")
    dni_input = st.text_input("DNI", max_chars=8)
    
    if st.button("Ingresar"):
        if dni_input:
            # Buscar en la colección "documentos" el ID correspondiente al DNI
            doc_ref = db.collection("documentos").document(dni_input)
            doc = doc_ref.get()
            
            if doc.exists:
                # Guardar la info de Firestore en la memoria de Streamlit
                st.session_state.user_data = doc.to_dict()
                st.rerun() # Recargar la página para entrar al chat
            else:
                st.error("Documento no encontrado en la base de datos.")
    st.stop() # Detiene la ejecución aquí hasta que el usuario se loguee

# 5. Extraer los datos mapeando a tu estructura de Firestore
user = st.session_state.user_data

nombres = user.get("nombres", "")
apellidos = user.get("apellidos", "")
afp_depositada = "Sí" if user.get("afp_depositada", False) else "No"
cts_pagada = "Sí" if user.get("cts_pagada", False) else "No"
cupones = user.get("cupones", 0)
remuneracion_anual = user.get("remuneracion_anual", "0")
# Los beneficios son un array en Firestore, los unimos con comas
beneficios_lista = user.get("beneficios", [])
beneficios_texto = ", ".join(beneficios_lista) if beneficios_lista else "Ninguno"

# 6. Construir el Prompt del Sistema con los datos reales
SYSTEM_PROMPT = f"""
Eres un asistente virtual amable del área de Recursos Humanos. 
Estás conversando con el colaborador: {nombres} {apellidos}.

Aquí tienes su información actual sacada de la base de datos:
- AFP depositada: {afp_depositada}
- CTS pagada: {cts_pagada}
- Cupones disponibles: {cupones}
- Remuneración anual: S/ {remuneracion_anual}
- Beneficios corporativos: {beneficios_texto}

Tu objetivo es responder a sus preguntas basándote ÚNICAMENTE en esta información. 
Si el colaborador te pregunta sobre un dato que no está en esta lista, dile amablemente que por el momento no tienes acceso a esa información. Sé breve y profesional.
"""

# 7. Interfaz de Chat (Bot)
st.write(f"¡Hola, **{nombres} {apellidos}**! 👋")
if st.button("Cerrar sesión"):
    st.session_state.user_data = None
    st.session_state.chat_history = []
    st.rerun()

st.divider()

# Inicializar historial de chat
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Mostrar mensajes anteriores
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input de usuario
user_input = st.chat_input("Pregúntame sobre tus beneficios, CTS, AFP o remuneración...")

if user_input:
    # 1. Guardar y mostrar mensaje del usuario
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Construir el arreglo de mensajes para la API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(st.session_state.chat_history)

    # 3. Llamada a Groq (Modelo Llama 3)
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.5,
        )
        respuesta_texto = response.choices[0].message.content
    except Exception as e:
        respuesta_texto = f"Lo siento, ocurrió un error al consultar: `{e}`"

    # 4. Mostrar y guardar respuesta del asistente
    with st.chat_message("assistant"):
        st.markdown(respuesta_texto)
    
    st.session_state.chat_history.append({"role": "assistant", "content": respuesta_texto})