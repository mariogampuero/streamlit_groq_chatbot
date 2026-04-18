import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

# Configuración inicial de la página
st.set_page_config(page_title="Chatbot de RRHH", page_icon="🏢", layout="centered")

# Cargar la API key de forma segura [cite: 213]
load_dotenv() # No falla si .env no existe [cite: 214]
API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")

if not API_KEY:
    st.error("Falta GROQ_API_KEY en .env o en st.secrets.")
    st.stop()

client = Groq(api_key=API_KEY)

# Inicializar el historial de chat [cite: 218]
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] # [{"role": "user"/"assistant", "content": "..."}]

# Definir el rol y los "datos" del bot (Nuestra base de datos en texto)
SYSTEM_PROMPT = """Eres un asistente virtual de Recursos Humanos muy amable, profesional y experto. 
Tu rol es resolver las dudas de los empleados de la empresa sobre las políticas internas.
Utiliza ÚNICAMENTE la siguiente información para responder:
- Vacaciones: 30 días calendario al año por ley.
- Seguros: El seguro médico privado (EPS) está cubierto al 75% por la empresa.
- Remuneraciones: El sueldo base varía por puesto. Se paga CTS en mayo y noviembre. Las gratificaciones (14 sueldos al año) se dan en julio y diciembre. Las utilidades se reparten en marzo.
- Beneficios del empleado: 20% de descuento en la cadena de gimnasios SmartFit y acceso gratuito a la plataforma de cursos Platzi.
- Cupones: Cada empleado tiene derecho a 2 cupones de 'Día Libre' al año, canjeables previo aviso a su jefatura.

Si te preguntan algo que no está en esta lista o piden datos personales específicos, responde amablemente que para información detallada o confidencial deben enviar un correo directamente a rrhh@empresa.com."""

st.title("🏢 Chatbot de RRHH - Asistente del Empleado")
st.write("¡Hola! Soy tu asistente de Recursos Humanos. Pregúntame sobre tus vacaciones, seguros, pagos o beneficios corporativos.")

# Render del historial [cite: 223]
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Escribe tu pregunta aquí...")

if user_input:
    # Mostrar el mensaje del usuario [cite: 229]
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Construir mensajes para el modelo [cite: 232]
    messages = []
    if SYSTEM_PROMPT:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.extend(st.session_state.chat_history)

    # Llamar a la API solo si hay user_input [cite: 236]
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant", # Modelo gratuito y rápido de Groq 
            messages=messages,
            temperature=0.7, # Creatividad balanceada [cite: 246]
        )
        respuesta_texto = response.choices[0].message.content # objeto, no dict [cite: 247]
    except Exception as e:
        respuesta_texto = f"Lo siento, ocurrió un error al llamar a la API: `{e}`"

    # Mostrar respuesta del asistente [cite: 250]
    with st.chat_message("assistant"):
        st.markdown(respuesta_texto)

    # Guardar en historial [cite: 252]
    st.session_state.chat_history.append({"role": "assistant", "content": respuesta_texto})