import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# 1. INICIALIZAR FIREBASE (Evitar reinicialización)
if not firebase_admin._apps:
    # En local usa el JSON, en Streamlit Cloud podrías usar secretos
    try:
        cred = credentials.Certificate("firebase-key.json")
        firebase_admin.initialize_app(cred)
    except:
        # Esto es para cuando lo subas a Streamlit Cloud usando secretos
        import json
        firebase_creds = dict(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. CONFIGURACIÓN GROQ
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY") or st.secrets["GROQ_API_KEY"])

st.title("🏢 RRHH Inteligente con Firebase")

# 3. FLUJO DE AUTENTICACIÓN
if "empleado_data" not in st.session_state:
    st.subheader("Bienvenido. Por favor identifícate:")
    dni_input = st.text_input("Ingresa tu DNI:")
    nombre_input = st.text_input("Ingresa tu nombre completo:")
    
    if st.button("Ingresar"):
        if dni_input and nombre_input:
            # Buscar en Firebase
            doc_ref = db.collection("empleados").document(dni_input)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                # Validar nombre simple (opcional)
                st.session_state.empleado_data = data
                st.success(f"Bienvenido/a {data['nombre']}")
                st.rerun()
            else:
                st.error("DNI no encontrado en la base de datos.")
        else:
            st.warning("Por favor completa ambos campos.")
    st.stop() # No mostrar el chat hasta que se loguee

# 4. CHAT UNA VEZ LOGUEADO
user_data = st.session_state.empleado_data

# Construimos un contexto ultra específico con los datos de Firebase
CONTEXTO_PERSONALIZADO = f"""
Eres el asistente de RRHH. Estás atendiendo a {user_data['nombre']}.
Datos actuales del empleado desde la base de datos:
- Remuneración: S/ {user_data['remuneracion']}
- Cupones disponibles: {user_data['cupones']}
- ¿CTS Pagada?: {'Sí, ambas cuotas' if user_data['cts_pagada'] else 'No, pendiente'}
- ¿AFP Depositada?: {'Sí' if user_data['afp_depositada'] else 'No'}
- Beneficios actuales: {', '.join(user_data['beneficios'])}
"""

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

user_input = st.chat_input("¿Qué duda tienes sobre tus pagos o beneficios?")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"): st.markdown(user_input)

    messages = [
        {"role": "system", "content": CONTEXTO_PERSONALIZADO},
        *st.session_state.chat_history
    ]

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages
    )
    
    answer = response.choices[0].message.content
    with st.chat_message("assistant"): st.markdown(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})