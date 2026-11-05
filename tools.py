"""

ARCHIVO: tools.py
POR QUÉ EXISTE ESTE ARCHIVO:
Define las herramientas (Tools) atómicas de cálculo matemático que el Agente Coordinador 
podrá invocar libremente mediante 'Tool Calling'.

REGLAS PEDAGÓGICAS Y RESTRICCIONES DADAS POR EL PROMPT:
1. Las funciones básicas son suma, resta, multiplicación y división.
2. La potenciación NO puede usar '**' ni 'math.pow()'.
    Debe construirse mediante
   recursividad llamando internamente a la herramienta de multiplicación.
3. Manejo de excepciones claro para evitar que un fallo (ej: división por cero) rompa el grafo.

"""

from langchain_core.tools import tool
from logger_config import logger


@tool
def sumar(a: float, b: float) -> float:
    """Suma dos números reales 'a' y 'b'."""
    logger.info(f"[TOOL INVOCADA] ➕ sumar(a={a}, b={b})")
    return a + b


@tool
def restar(a: float, b: float) -> float:
    """Resta el número 'b' al número 'a' (a - b)."""
    logger.info(f"[TOOL INVOCADA] ➖ restar(a={a}, b={b})")
    return a - b


@tool
def multiplicar(a: float, b: float) -> float:
    """Multiplica dos números reales 'a' y 'b'."""
    logger.info(f"[TOOL INVOCADA] ✖️ multiplicar(a={a}, b={b})")
    return a * b


@tool
def dividir(a: float, b: float) -> str:
    """Divide el número 'a' por 'b' (a / b). Captura división por cero."""
    logger.info(f"[TOOL INVOCADA] ➗ dividir(a={a}, b={b})")
    if b == 0:
        msg = "ERROR: No es posible dividir entre cero."
        logger.error(f"[TOOL ERROR] {msg}")
        return msg
    return str(a / b)


@tool
def potenciar(base: float, exponente: int) -> str:
    """
    Calcula la potencia de una base elevada a un exponente entero.

    POR QUÉ SE HACE RECURSIVO CON MULTIPLICACIÓN:
    Cumple la restricción directa del ejercicio: no usar el operador '**'.
    Llama recursivamente a la función 'multiplicar' para resolver la operación.
    """
    logger.info(f"[TOOL INVOCADA] 🚀 potenciar(base={base}, exponente={exponente})")

    # Validación de entero para garantizar una recursión didáctica limpia
    if not isinstance(exponente, int) or exponente < 0:
        return "ERROR: Para este ejemplo didáctico, el exponente debe ser un número entero no negativo."

    # Casos base de la potencia
    if exponente == 0:
        return "1.0"
    if exponente == 1:
        return str(float(base))

    # Paso recursivo: base * potenciar(base, exponente - 1)
    # Invocamos directamente el cuerpo de la herramienta multiplicar para registrar su uso
    sub_potencia = float(potenciar.invoke({"base": base, "exponente": exponente - 1}))
    resultado_final = multiplicar.invoke({"a": base, "b": sub_potencia})

    return str(resultado_final)


# Colección completa de herramientas para enlazar con el Agente Coordinador
HERRAMIENTAS_MATEMATICAS = [sumar, restar, multiplicar, dividir, potenciar]