#!/bin/bash
# Instala librerías críticas primero
pip install pendulum>=3.0.0,<4.0.0
pip install tenacity>=8.2.0
pip install highrise-bot-sdk --no-deps

# Instala el resto de librerías de requirements.txt
pip install -r requirements.txt

# Ejecuta tu run.py
python run.py
