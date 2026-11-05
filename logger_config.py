"""
ARCHIVO: logger_config.py
POR QUÉ EXISTE ESTE ARCHIVO:
Para cumplir con el requerimiento de seguimiento local detallado. Configura un sistema de
logueo unificado (Python logging) que graba todas las acciones de los agentes,
decisiones del grafo e intervenciones humanas tanto en la consola (con colores/iconos)
como en un archivo persistente en disco ('agente_matematico.log').
"""

import logging
import sys
import os

# Nombre del archivo de log local en la carpeta raíz
LOG_FILENAME = "agente_matematico.log"


def setup_logger():
    """
    Configura y devuelve un logger personalizado para el proyecto.

    POR QUÉ SE HACE ASÍ:
    Se agregan dos 'handlers':
    1. FileHandler: para mantener persistencia física en el disco del historial de eventos.
    2. StreamHandler: para mostrar los logs en vivo en la pantalla de la terminal.
    """
    logger = logging.getLogger("AgenteMatematico")
    logger.setLevel(logging.DEBUG)

    # Evitamos duplicación de logs si el logger ya fue instanciado previamente
    if logger.handlers:
        return logger

    # Formato claro con timestamp, nivel de severidad y el mensaje explicativo
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler 1: Persistencia local en archivo (.log)
    file_handler = logging.FileHandler(LOG_FILENAME, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Handler 2: Impresión limpia por consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    return logger


# Instancia global lista para ser importada en cualquier parte del código
logger = setup_logger()