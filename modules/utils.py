import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

def cargar_configuracion() -> Dict[str, Any]:
    """
    Carga la configuración desde los archivos JSON.
    
    Returns:
        Configuración completa del sistema
    """
    try:
        # Cargar configuración principal
        with open('config/config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Cargar keywords
        with open('config/keywords.json', 'r', encoding='utf-8') as f:
            keywords = json.load(f)
        
        # Cargar regiones
        with open('config/regiones.json', 'r', encoding='utf-8') as f:
            regiones = json.load(f)
        
        # Combinar todo
        config['keywords'] = keywords
        config['regiones'] = regiones
        
        return config
    except Exception as e:
        print(f"Error al cargar configuración: {str(e)}")
        # Valores por defecto si falla la carga
        return {
            "google_api": {"api_key": "", "cx_id": "", "resultados_por_busqueda": 5},
            "selenium": {"headless": True, "timeout": 10},
            "delays": {"entre_busquedas": [3, 6], "entre_extracciones": [1, 3]},
            "modo_prueba": True,
            "logs": {"level": "INFO", "rotation": True},
            "guardado": {"intervalo": 300},
            "keywords": [],
            "regiones": {"comunidades": [], "ciudades": {}}
        }

def setup_logging() -> logging.Logger:
    """
    Configura el sistema de logging con rotación de archivos.
    
    Returns:
        Logger principal
    """
    # Crear directorio de logs si no existe
    os.makedirs('logs', exist_ok=True)
    
    log_filename = f'logs/prospeccion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('Prospector')

def filtrar_parametros_prueba(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Limita los parámetros de búsqueda en modo prueba.
    
    Args:
        config: Configuración completa
    
    Returns:
        Configuración ajustada para pruebas
    """
    if not config.get('modo_prueba', False):
        return config
    
    # Copia para no modificar el original
    prueba_config = config.copy()
    
    # Limitar keywords
    prueba_config['keywords'] = prueba_config['keywords'][:2]
    
    # Limitar comunidades
    prueba_config['regiones']['comunidades'] = prueba_config['regiones']['comunidades'][:2]
    
    # Limitar ciudades
    for comunidad in prueba_config['regiones']['comunidades']:
        if comunidad in prueba_config['regiones']['ciudades']:
            prueba_config['regiones']['ciudades'][comunidad] = prueba_config['regiones']['ciudades'][comunidad][:2]
    
    return prueba_config