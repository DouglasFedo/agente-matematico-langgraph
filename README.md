# agente-matematico-langgraph
Agente matemático local con LangGraph y Ollama -  con orquedataor y human in the loop

# 🤖 Agente Matemático Didáctico con LangGraph y Ollama

Este proyecto implementa un agente conversacional inteligente especializado en resolución matemática, construido utilizando **LangChain**, **LangGraph**, **Ollama** (ejecutándose localmente con `llama3.1`) y monitoreo de trazas mediante **LangSmith**.

## 📂 Estructura del Proyecto
- `agent.py`: Núcleo del agente, definición del grafo de estados y lógica de control.
- `tools.py`: Herramientas matemáticas y operativas disponibles para el agente.
- `logger_config.py`: Sistema de logging dual (consola y archivo local).
- `main.py`: Interfaz interactiva de ejecución con soporte para persistencia (`MemorySaver`).

## 🚀 Requisitos previos
1. Tener instalado [Ollama](https://ollama.com/) en tu equipo.
2. Descargar el modelo compatible:
   ```bash
   ollama pull llama3.1
