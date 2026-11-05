"""
ARCHIVO: main.py
POR QUÉ EXISTE ESTE ARCHIVO:
Es el punto de entrada ejecutable de la aplicación para el Agente Matemático Didáctico.
Gestiona:
1. El bucle interactivo de la terminal.
2. La persistencia por sesión mediante identificadores únicos (Thread ID).
3. La interrupción del flujo para el Human-in-the-Loop (HITL).
4. La validación estricta de la entrada del usuario para garantizar que las fórmulas corregidas sean matemáticamente válidas antes de continuar.
"""

import sys
import uuid
import re
from langchain_core.messages import HumanMessage
from agent import grafo_compilado
from logger_config import logger

def ejecutar_solicitud(entrada_usuario: str):
    """
    Gestiona la ejecución completa del flujo del grafo para una consulta matemática dada,
    interceptando el punto de validación humana (HITL) y reanudando la ejecución.
    """
    # Generamos un ID de hilo único para la sesión actual (Permite persistencia y aislamiento con MemorySaver)
    thread_id = str(uuid.uuid4())
    config_hilo = {"configurable": {"thread_id": thread_id}}

    logger.info("==================================================")
    logger.info(f"[INICIO OPERACIÓN] Solicitud: '{entrada_usuario}' | Thread ID: {thread_id}")

    # Estado inicial que enviamos al grafo al arrancar
    estado_inicial = {
        "messages": [HumanMessage(content=entrada_usuario)],
        "formula_traducida": None,
        "requirio_traduccion": False,
        "validacion_humana": None,
        "es_incoherente": False
    }

    logger.info("[EJECUCIÓN] Iniciando flujo del grafo...")
    # Corremos el grafo hasta que se complete o llegue al punto de interrupción (interrupt_before)
    for evento in grafo_compilado.stream(estado_inicial, config_hilo):
        pass

    # Obtenemos el estado actual guardado en el Checkpointer
    estado_actual = grafo_compilado.get_state(config_hilo)

    # Verificamos si el grafo se detuvo en el nodo de Human-in-the-Loop
    if estado_actual.next and "human_in_the_loop" in estado_actual.next:
        formula_obtenida = estado_actual.values.get("formula_traducida")

        logger.info("\n" + "="*60)
        logger.info("[HUMAN IN THE LOOP - INTERVENCIÓN REQUERIDA]")
        logger.info(f"El Agente Traductor (Ollama) interpretó la frase como: '{formula_obtenida}'")
        logger.info("="*60)

        print(f"\n👉 [OLLAMA TRADUCCIÓN]: '{formula_obtenida}'")

        formula_final = None
        registro_humano = None

        # Bucle estricto de validación humana para evitar fórmulas incorrectas o letras sueltas
        while True:
            opcion = input("¿Deseas aprobar esta traducción? [S/n] o escribe la fórmula corregida (ej: 3*4): ").strip()

            if opcion.lower() in ["s", "si", "sí", ""]:
                logger.info("[HITL REGISTRO] 🟢 El humano APROBÓ la traducción sin cambios.")
                registro_humano = {"accion": "APROBADO", "formula_original": formula_obtenida, "formula_final": formula_obtenida}
                formula_final = formula_obtenida
                break

            # Determinamos si el usuario rechazó con 'n' o ingresó una corrección directa
            candidato_formula = formula_obtenida if opcion.lower() in ["n", "no"] else opcion

            if opcion.lower() in ["n", "no"]:
                candidato_formula = input("Por favor, ingresa la fórmula matemática correcta (ej: 3*4+20): ").strip()

            # VALIDACIÓN ESTRICTA: Solo permitimos números, espacios y operadores matemáticos válidos (+, -, *, /, ^, paréntesis)
            # Esto rechaza automáticamente letras sueltas ('j', 'hola', etc.) o texto incoherente.
            es_formula_valida = bool(re.match(r'^[0-9\.\s\+\-\*\/\^\(\)]+$', candidato_formula))

            if es_formula_valida and candidato_formula:
                logger.info(f"[HITL REGISTRO] 🟡 El humano validó/corrigió la fórmula a: '{candidato_formula}'")
                registro_humano = {"accion": "CORREGIDO", "formula_original": formula_obtenida, "formula_final": candidato_formula}
                formula_final = candidato_formula
                break
            else:
                print("❌ [ERROR DE VALIDACIÓN]: La fórmula ingresada contiene letras o caracteres no válidos. Debe ser una expresión matemática (ej: 3+8). Intenta nuevamente.")
                logger.warning(f"[HITL VALIDACIÓN] El usuario intentó ingresar una fórmula inválida/incoherente: '{candidato_formula}'")

        # Actualizamos el estado del grafo con la fórmula ya validada y segura
        grafo_compilado.update_state(
            config_hilo,
            {
                "formula_traducida": formula_final,
                "validacion_humana": registro_humano,
                "es_incoherente": False
            }
        )

        logger.info("[EJECUCIÓN] Reanudando el grafo tras la validación humana...")
        # Reanudamos la ejecución del grafo pasando None (continúa desde el punto donde se pausó)
        for evento in grafo_compilado.stream(None, config_hilo):
            pass

    # Estado Final recopilado del checkpointer
    estado_final = grafo_compilado.get_state(config_hilo).values

    logger.info("\n--------------------------------------------------")
    logger.info("[RESUMEN Y TRACKING DE LA OPERACIÓN]")
    logger.info(f" 📥 Entrada Original      : {entrada_usuario}")
    logger.info(f" 🔀 Requirió Traducción   : {estado_final.get('requirio_traduccion')}")
    logger.info(f" 🦙 Formula Traducida     : {estado_final.get('formula_traducida')}")
    logger.info(f" 👤 Validación Humana     : {estado_final.get('validacion_humana')}")
    logger.info(f" ⚠️ Es Incoherente        : {estado_final.get('es_incoherente')}")

    ultimo_msg = estado_final["messages"][-1].content
    logger.info(f" 🏁 Resultado Final Output : {ultimo_msg}")
    logger.info("--------------------------------------------------\n")

    print(f"\n✨ RESULTADO FINAL: {ultimo_msg}\n")


def main():
    """
    Bucle principal de la consola interactiva.
    """
    print("="*60)
    print("🤖 BIENVENIDO AL AGENTE MATEMÁTICO DIDÁCTICO MULTI-NODO")
    print("Soporta: Suma, Resta, Multiplicación, División y Potencia recursiva.")
    print("Escribe 'salir' para finalizar.")
    print("="*60 + "\n")

    while True:
        try:
            usuario_input = input("Ingrese operación > ").strip()
            if not usuario_input:
                continue
            if usuario_input.lower() in ["salir", "exit", "quit"]:
                print("¡Hasta luego!")
                break

            ejecutar_solicitud(usuario_input)

        except KeyboardInterrupt:
            print("\nOperación cancelada por el usuario. Saliendo...")
            sys.exit(0)
        except Exception as e:
            logger.error(f"[ERROR INESPERADO] {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()