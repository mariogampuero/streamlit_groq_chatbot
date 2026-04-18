import os
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from groq import Groq

# 1. Configuración de la página
st.set_page_config(page_title="RRHH Hub PUCP", page_icon="🏢", layout="wide")

# 2. Inicializar conexión a Firebase
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred_dict = dict(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# 3. Inicializar conexión a Groq
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("Falta la llave GROQ_API_KEY en st.secrets.")
    st.stop()
client = Groq(api_key=GROQ_API_KEY)

# --- LÓGICA DE DATOS CON FIREBASE ---

def obtener_todos_los_colaboradores_publico(dni_excluir):
    """Trae solo la información PÚBLICA de los demás empleados."""
    docs = db.collection("documentos").stream()
    lista_publica = []
    
    for d in docs:
        if d.id != dni_excluir: # Excluir al usuario actual
            data = d.to_dict()
            # Extraer SOLO lo que es público por políticas de privacidad
            info_publica = {
                "nombres": data.get("nombres", ""),
                "apellidos": data.get("apellidos", ""),
                "puesto": data.get("puesto", "Empleado"),
                "hobbies": data.get("hobbies", [])
            }
            lista_publica.append(info_publica)
            
    return lista_publica

def actualizar_hobbies(dni, lista_hobbies):
    """Guarda o actualiza el array de hobbies en Firestore."""
    doc_ref = db.collection("documentos").document(dni)
    doc_ref.update({"hobbies": lista_hobbies})

# --- INTERFAZ DE USUARIO ---

st.title("🤖 Bot Asistente de RRHH & Networking - PUCP")

if "user_data" not in st.session_state:
    st.session_state.user_data = None

# PANTALLA DE LOGIN
if st.session_state.user_data is None:
    st.subheader("Bienvenido al portal del colaborador")
    dni_input = st.text_input("Ingresa tu DNI para empezar:", max_chars=8)
    if st.button("Ingresar"):
        if dni_input:
            doc_ref = db.collection("documentos").document(dni_input)
            doc = doc_ref.get()
            if doc.exists:
                st.session_state.user_data = doc.to_dict()
                st.session_state.user_dni = dni_input
                st.rerun()
            else:
                st.error("DNI no registrado en la base de datos.")
        else:
            st.warning("Por favor, ingresa un DNI.")
    st.stop()

# --- USUARIO LOGUEADO ---
user = st.session_state.user_data
dni_actual = st.session_state.user_dni

# BARRA LATERAL: Gestión de Hobbies y Perfil
with st.sidebar:
    st.header(f"Hola, {user.get('nombres')} 👋")
    st.write(f"**Puesto:** {user.get('puesto', 'No asignado')}")
    
    st.divider()
    st.subheader("🎨 Mis Hobbies")
    hobbies_actuales = user.get("hobbies", [])
    
    # Input para nuevos hobbies (separados por coma)
    nuevo_hobby_str = st.text_area("Edita tus hobbies (separados por comas):", 
                                   value=", ".join(hobbies_actuales))
    
    if st.button("Guardar Hobbies"):
        # Convertir string a lista limpia
        lista_nueva = [h.strip() for h in nuevo_hobby_str.split(",") if h.strip()]
        actualizar_hobbies(dni_actual, lista_nueva)
        # Actualizar sesión local para que el bot se entere de inmediato
        st.session_state.user_data["hobbies"] = lista_nueva
        st.success("¡Hobbies actualizados en la base de datos!")
        st.rerun()

    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state.user_data = None
        st.session_state.chat_history = []
        st.rerun()

# --- PROCESAMIENTO DE VARIABLES DEL USUARIO PARA EL BOT ---
nombres = user.get("nombres", "")
apellidos = user.get("apellidos", "")
puesto = user.get("puesto", "No asignado")
afp_depositada = "Sí" if user.get("afp_depositada", False) else "No"
cts_pagada = "Sí" if user.get("cts_pagada", False) else "No"
cupones = user.get("cupones", 0)
remuneracion_anual = user.get("remuneracion_anual", "0")
hobbies_usuario = ", ".join(user.get("hobbies", []))

beneficios_lista = user.get("beneficios", [])
beneficios_texto = ", ".join(beneficios_lista) if beneficios_lista else "Ninguno"

# --- PREPARAR CONTEXTO DE COMPAÑEROS PARA EL BOT ---
companeros_publicos = obtener_todos_los_colaboradores_publico(dni_actual)

contexto_companeros = ""
for c in companeros_publicos:
    n = f"{c['nombres']} {c['apellidos']}"
    p = c['puesto']
    h = ", ".join(c['hobbies']) if c['hobbies'] else "No especificados"
    contexto_companeros += f"- {n} (Puesto: {p}). Hobbies: {h}\n"

# --- SYSTEM PROMPT DEFINITIVO ---
SYSTEM_PROMPT = f"""
Eres un asistente virtual amable y experto del área de Recursos Humanos y Networking interno. 
Estás conversando con el colaborador: {nombres} {apellidos}.

DATOS PRIVADOS DEL USUARIO ACTUAL (Solo puedes hablar de esto con él):
- Puesto: {puesto}
- Sus Hobbies: {hobbies_usuario}
- Estado del depósito de AFP: {afp_depositada}
- Estado del pago de CTS: {cts_pagada}
- Cupones de día libre disponibles: {cupones}
- Remuneración anual bruta: S/ {remuneracion_anual}
- Beneficios corporativos activos: {beneficios_texto}

DIRECTORIO DE COMPAÑEROS PARA NETWORKING (Datos públicos de los demás):
{contexto_companeros}

CONCEPTOS DE RRHH (Reglas a respetar):
- CTS: La empresa deposita este dinero. El colaborador no lo paga. "Sí" significa que la empresa ya depositó.
- AFP: La empresa retiene el porcentaje y lo deposita en la AFP. "Sí" significa que la empresa ya hizo el depósito.
- Cupones: Días o medios días libres a disposición del colaborador.

REGLAS DE RESPUESTA:
1. NETWORKING POR HOBBIES: Si el usuario pregunta con quién compartir hobbies, busca coincidencias en la lista de compañeros y menciónalos por su nombre.
2. AYUDA POR PUESTO: Si el usuario tiene un problema, sugiérele hablar con la persona adecuada de la lista según su 'Puesto' (ej. TI, Sistemas, Recursos Humanos, Finanzas).
3. PRIVACIDAD ESTRICTA: Por políticas de seguridad, tienes PROHIBIDO hablar sobre sueldos, AFP, CTS, cupones o beneficios de otras personas que no sean el usuario actual ({nombres}). De los demás colaboradores SOLO conoces sus nombres, su puesto y sus hobbies. Si el usuario te pregunta por datos privados de otra persona, dile que por políticas de privacidad no puedes revelar esa información.
4. Mantén un tono profesional, empático, alegre y que fomente la cultura de la empresa.
"""

# --- INTERFAZ DEL CHAT ---
st.write(f"¡Hola de nuevo, **{nombres}**! Puedes preguntarme sobre tus pagos, tus beneficios, o incluso pedirme que te contacte con personas que compartan tus intereses.")
st.divider()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ej: ¿Con quién comparto hobbies? / ¿Ya depositaron mi CTS?")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(st.session_state.chat_history)

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4,
        )
        respuesta_texto = response.choices[0].message.content
    except Exception as e:
        respuesta_texto = f"Error al procesar la solicitud: {e}"

    with st.chat_message("assistant"):
        st.markdown(respuesta_texto)
    st.session_state.chat_history.append({"role": "assistant", "content": respuesta_texto})