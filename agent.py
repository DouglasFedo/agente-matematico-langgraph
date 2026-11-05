"""
ARCHIVO: agent.py
POR QUÉ EXISTE ESTE ARCHIVO:
Es el núcleo donde se construye la orquestación multi-agente usando LangGraph.
Define:
1. El Estado Global (State) para persistir mensajes, la fórmula traducida y el tracking de Human-in-the-Loop.
2. El Nodo 'Traductor' (usa Ollama para convertir texto a expresión matemática).
3. El Nodo 'Humano' (interrupción y validación de la traducción).
4. El Nodo 'Coordinador' (analiza la expresión y llama a las tools).
5. El Nodo 'Herramientas' (ToolNode que ejecuta las funciones de tools.py).
6. El Checkpointer (MemorySaver) para darle persistencia local y estado a las conversaciones.
"""

import os
import re
from typing import TypedDict, Annotated, List, Optional
from dotenv import load_dotenv

from langchain_core.messages import ToolMessage

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from logger_config import logger
from tools import HERRAMIENTAS_MATEMATICAS



load_dotenv()


# ============================================================================
# 1. ESTADO GLOBAL DEL GRAFO (STATE)
# ============================================================================
class EstadoAgenteMatematico(TypedDict):
    """
    POR QUÉ DEFINIMOS ESTE ESTADO:
    LangGraph hace pasar un objeto de estado a través de todos los nodos.
    - 'messages': Lista acumulativa de mensajes (conversación) gestionada con 'add_messages'.
    - 'formula_traducida': Guarda la traducción matemática obtenida por el LLM o la corregida por el humano.
    - 'requirio_traduccion': Flag booleano para el tracking local/LangSmith.
    - 'validacion_humana': Registra si el humano aprobó o modificó la fórmula.
    - 'es_incoherente': Marca si la entrada fue catalogada como sin sentido.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    formula_traducida: Optional[str]
    requirio_traduccion: bool
    validacion_humana: Optional[dict]
    es_incoherente: bool


# ============================================================================
# 2. MODELO OLLAMA Y BINDING DE TOOLS
# ============================================================================
# Instanciamos el modelo local mediante Ollama
modelo_nombre = os.getenv("OLLAMA_MODEL", "llama3.1")
base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

logger.info(f"[SETUP AGENTE] Inicializando Ollama local en {base_url} con modelo: {modelo_nombre}")

llm_traductor = ChatOllama(model=modelo_nombre, base_url=base_url, temperature=0.0)
llm_coordinador = ChatOllama(model=modelo_nombre, base_url=base_url, temperature=0.0)

# El Agente Coordinador resuelve ÚNICAMENTE a través de sus tools
llm_coordinador_con_tools = llm_coordinador.bind_tools(HERRAMIENTAS_MATEMATICAS)


# ============================================================================
# 3. NODO EVALUADOR DE ENTRADA / TRADUCTOR (OLLAMA)
# ============================================================================
def nodo_traductor(state: EstadoAgenteMatematico):
    """
    POR QUÉ EXISTE ESTE NODO:
    Analiza el mensaje del usuario.
    1. Si ya es una fórmula clara (ej: "3*5"), detecta que no necesita traducción.
    2. Si es texto (ej: "tres por cinco"), llama a Ollama para traducirlo a fórmula.
    3. Si es una frase disparatada ("mi perro tiene 3 colas"), la marca como incoherente.
    """
    logger.info("--------------------------------------------------")
    logger.info("[NODO TRADUCTOR] 🧠 Analizando entrada del usuario...")

    ultimo_mensaje = state["messages"][-1].content.strip()
    logger.info(f"[NODO TRADUCTOR] Entrada recibida: '{ultimo_mensaje}'")

    # Evaluación rápida mediante Regex para ver si ya es una expresión directa
    es_formula_directa = bool(re.match(r'^[0-9\.\s\+\-\*\/\^]+$', ultimo_mensaje))

    if es_formula_directa:
        logger.info("[NODO TRADUCTOR] ⚡ La entrada ya es una fórmula matemática válida. No requiere a Ollama.")
        return {
            "formula_traducida": ultimo_mensaje,
            "requirio_traduccion": False,
            "es_incoherente": False
        }

    # Si es texto en lenguaje natural, invocamos a Ollama
    prompt_sistema = SystemMessage(content=(
        "Eres un traductor estricto de texto en español a expresiones matemáticas numéricas simplificadas.\n"
        "Reglas:\n"
        "1. Si el texto es una operación inteligible como 'tres mas ocho' o 'dos elevado a cuatro', responde ÚNICAMENTE la fórmula en números y símbolos (ej: '3+8' o '2^4').\n"
        "2. Si el texto es incoherente o sin sentido matemático (ej: 'mi perro tiene 3 colas', 'raiz de un tercio por ocho quintos'), responde exactamente la palabra 'INCOHERENTE'.\n"
        "3. NO agregues explicaciones, ni puntos finales, ni comentarios extras."
    ))

    logger.info("[NODO TRADUCTOR] 🦙 Consultando a Ollama para traducir texto a fórmula...")
    respuesta_llm = llm_traductor.invoke([prompt_sistema, HumanMessage(content=ultimo_mensaje)])
    traduccion = respuesta_llm.content.strip()

    logger.info(f"[NODO TRADUCTOR] Respuesta cruda de Ollama: '{traduccion}'")

    if "INCOHERENTE" in traduccion.upper():
        logger.warning("[NODO TRADUCTOR] ⚠️ Se ha detectado una consulta incoherente o no resoluble.")
        return {
            "formula_traducida": None,
            "requirio_traduccion": True,
            "es_incoherente": True
        }

    logger.info(f"[NODO TRADUCTOR] ✅ Traducción exitosa obtenida por Ollama: '{traduccion}'")
    return {
        "formula_traducida": traduccion,
        "requirio_traduccion": True,
        "es_incoherente": False
    }


# ============================================================================
# 4. NODO HUMAN-IN-THE-LOOP (PUNTO DE INTERRUPCIÓN)
# ============================================================================
def nodo_human_in_the_loop(state: EstadoAgenteMatematico):
    """
    POR QUÉ EXISTE ESTE NODO:
    Actúa como un 'checkpoint' pasivo dentro del grafo. Cuando el flujo llega aquí,
    el grafo se pausa automáticamente para que el script 'main.py' solicite la confirmación
    o corrección al operador humano.
    """
    logger.info("[NODO HITL] 🙋 Esperando validación o intervención del operador humano...")
    return {}


# ============================================================================
# 5. NODO COORDINADOR (ORQUESTADOR CON TOOLS - CORREGIDO ANTI-BUCLE)
# ============================================================================
def nodo_coordinador(state: EstadoAgenteMatematico):
    """
    POR QUÉ SE MODIFICÓ:
    Ahora verifica si ya se ejecutó una herramienta (ToolMessage en el historial).
    - Si NO se ha ejecutado, invoca al LLM CON tools para que decida qué herramienta usar.
    - Si YA se ejecutó, invoca al LLM SIN tools para obligarlo a procesar el resultado
      y redactar la respuesta final en texto, evitando el bucle infinito.
    """
    logger.info("[NODO COORDINADOR] 🎯 Procesando estado actual...")

    if state.get("es_incoherente"):
        mensaje_error = AIMessage(
            content="No se puede resolver la operación solicitada ya que la instrucción no es coherente o válida.")
        logger.warning(f"[NODO COORDINADOR] Cancelando ejecución por incoherencia.")
        return {"messages": [mensaje_error]}

    formula = state.get("formula_traducida")
    messages = state.get("messages", [])

    # Verificamos si el último mensaje es el resultado de una herramienta
    ultimo_mensaje = messages[-1] if messages else None
    viene_de_tool = isinstance(ultimo_mensaje, ToolMessage)

    prompt_sistema = SystemMessage(content=(
        "Eres un agente coordinador matemático. Tu trabajo es resolver la expresión dada usando las herramientas disponibles.\n"
        "Reglas:\n"
        "1. Para operaciones con exponente (ej: '2^4'), usa la herramienta 'potenciar'.\n"
        "2. Si ya recibiste el resultado de una herramienta (ToolMessage), NO vuelvas a llamar a ninguna herramienta; redacta la respuesta final para el usuario con el resultado obtenido."
    ))

    if viene_de_tool:
        logger.info(
            "[NODO COORDINADOR] 🔒 La herramienta ya fue ejecutada. Usando LLM sin tools para dar la respuesta final.")
        # Invocamos el modelo SIN herramientas enlazadas para que escriba la conclusión
        respuesta = llm_coordinador.invoke([prompt_sistema] + messages)
    else:
        logger.info(f"[NODO COORDINADOR] 🛠️ Analizando fórmula para invocar Tool: '{formula}'")
        # Primera vez: enviamos la fórmula traducida con las herramientas habilitadas
        mensaje_formula = HumanMessage(content=f"Resuelve la siguiente fórmula usando herramientas: {formula}")
        respuesta = llm_coordinador_con_tools.invoke([prompt_sistema, mensaje_formula])

    return {"messages": [respuesta]}



# ============================================================================
# 6. ENRUTADO Y LÓGICA CONDICIONAL DE ARISTAS
# ============================================================================

# ============================================================================
# 6. ENRUTADO Y LÓGICA CONDICIONAL DE ARISTAS (CORREGIDO)
# ============================================================================
def evaluar_siguiente_paso_traduccion(state: EstadoAgenteMatematico):
    if state.get("es_incoherente"):
        return "coordinador"
    if state.get("requirio_traduccion"):
        return "human_in_the_loop"
    return "coordinador"


def evaluar_siguiente_paso_coordinador(state: EstadoAgenteMatematico):
    """
    Decide si el flujo continúa hacia las tools o finaliza.
    """
    ultimo_mensaje = state["messages"][-1]

    # Si el último mensaje es una ToolMessage, significa que el coordinador ya procesó
    # la respuesta de la herramienta en el paso anterior. Terminamos el grafo.
    if isinstance(ultimo_mensaje, ToolMessage):
        logger.info(
            "[ARISTA CONDICIONAL] 🏁 La herramienta devolvió el resultado y el coordinador respondió. Fin del ciclo.")
        return END

    if hasattr(ultimo_mensaje, "tool_calls") and ultimo_mensaje.tool_calls:
        logger.info("[ARISTA CONDICIONAL] 🔀 El Coordinador solicitó Tool. Redirigiendo a 'herramientas'.")
        return "herramientas"

    logger.info("[ARISTA CONDICIONAL] 🏁 El Coordinador ha finalizado. Terminando flujo.")
    return END



# ============================================================================
# 7. CONSTRUCCIÓN DEL GRAFO DE LANGGRAPH CON MEMORIA
# ============================================================================
workflow = StateGraph(EstadoAgenteMatematico)

# Agregar nodos al grafo
workflow.add_node("traductor", nodo_traductor)
workflow.add_node("human_in_the_loop", nodo_human_in_the_loop)
workflow.add_node("coordinador", nodo_coordinador)
workflow.add_node("herramientas", ToolNode(HERRAMIENTAS_MATEMATICAS))

# Punto de inicio
workflow.add_edge(START, "traductor")

# Arista condicional tras la traducción
workflow.add_conditional_edges(
    "traductor",
    evaluar_siguiente_paso_traduccion,
    {
        "human_in_the_loop": "human_in_the_loop",
        "coordinador": "coordinador"
    }
)

# Arista fija tras la intervención humana
workflow.add_edge("human_in_the_loop", "coordinador")

# Aristas condicionales del coordinador y sus herramientas
workflow.add_conditional_edges(
    "coordinador",
    evaluar_siguiente_paso_coordinador,
    {
        "herramientas": "herramientas",
        END: END
    }
)
# Retorno obligatorio de la tool ejecutada al coordinador
workflow.add_edge("herramientas", "coordinador")

# PERSISTENCIA LOCAL: MemorySaver permite guardar estados entre interrupciones (HITL)
memoria_persistencia = MemorySaver()

# Compilamos el grafo especificando la interrupción ANTES del nodo del coordinador si pasó por HITL
logger.info("[SETUP GRAFO] Compilando el Grafo con Interrupción en 'human_in_the_loop' y Checkpointer local...")
grafo_compilado = workflow.compile(
    checkpointer=memoria_persistencia,
    interrupt_before=["human_in_the_loop"]
)