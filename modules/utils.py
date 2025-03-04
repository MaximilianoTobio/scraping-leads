import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

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
        
        # Cargar filtros de búsqueda (si existe)
        filtros_busqueda = {}
        if os.path.exists('config/filtros_busqueda.json'):
            try:
                with open('config/filtros_busqueda.json', 'r', encoding='utf-8') as f:
                    filtros_busqueda = json.load(f)
                logging.getLogger('Utils').info("Filtros de búsqueda cargados correctamente")
            except Exception as e:
                logging.getLogger('Utils').error(f"Error al cargar filtros de búsqueda: {str(e)}")
        
        # Combinar todo
        config['keywords'] = keywords
        config['regiones'] = regiones
        config['filtros_busqueda'] = filtros_busqueda
        
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
            "regiones": {"comunidades": [], "ciudades": {}},
            "filtros_busqueda": {},
            "umbral_relevancia": 40,
            "filtrar_sin_telefono": False
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

def gestionar_contador_busquedas() -> Tuple[int, str]:
    """
    Gestiona el contador de búsquedas diarias, reiniciándolo si es un nuevo día.
    
    Returns:
        Tuple[int, str]: (búsquedas realizadas hoy, fecha actual en formato YYYY-MM-DD)
    """
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    ruta_contador = 'config/contador_busquedas.json'
    
    # Datos por defecto
    datos_contador = {
        "fecha": fecha_actual,
        "busquedas_realizadas": 0
    }
    
    # Verificar si existe el archivo y cargarlo
    if os.path.exists(ruta_contador):
        try:
            with open(ruta_contador, 'r', encoding='utf-8') as f:
                datos_contador = json.load(f)
                
            # Si es un nuevo día, reiniciar contador
            if datos_contador.get("fecha") != fecha_actual:
                datos_contador = {
                    "fecha": fecha_actual,
                    "busquedas_realizadas": 0
                }
                logging.getLogger('Prospector').info(f"Nuevo día detectado. Contador reiniciado a 0.")
            else:
                logging.getLogger('Prospector').info(f"Continuando con {datos_contador['busquedas_realizadas']} búsquedas previas realizadas hoy.")
                
        except Exception as e:
            logging.getLogger('Prospector').error(f"Error al cargar contador de búsquedas: {str(e)}")
    
    return datos_contador["busquedas_realizadas"], fecha_actual

def actualizar_contador_busquedas(busquedas_realizadas: int, fecha: str) -> None:
    """
    Actualiza y guarda el contador de búsquedas diarias.
    
    Args:
        busquedas_realizadas: Número de búsquedas realizadas
        fecha: Fecha actual en formato YYYY-MM-DD
    """
    ruta_contador = 'config/contador_busquedas.json'
    
    datos_contador = {
        "fecha": fecha,
        "busquedas_realizadas": busquedas_realizadas
    }
    
    try:
        os.makedirs('config', exist_ok=True)
        with open(ruta_contador, 'w', encoding='utf-8') as f:
            json.dump(datos_contador, f, ensure_ascii=False, indent=4)
        
        logging.getLogger('Prospector').info(f"Contador actualizado: {busquedas_realizadas} búsquedas realizadas el {fecha}")
    except Exception as e:
        logging.getLogger('Prospector').error(f"Error al guardar contador de búsquedas: {str(e)}")

def guardar_punto_control(estado: Dict[str, Any]) -> None:
    """Guarda el punto de control actual de la búsqueda."""
    ruta_checkpoint = 'config/checkpoint.json'
    
    try:
        os.makedirs('config', exist_ok=True)
        with open(ruta_checkpoint, 'w', encoding='utf-8') as f:
            json.dump(estado, f, ensure_ascii=False, indent=4)
        
        logging.getLogger('Prospector').info(f"Punto de control guardado: {estado['comunidad_actual']}, {estado['keyword_actual']}")
    except Exception as e:
        logging.getLogger('Prospector').error(f"Error al guardar punto de control: {str(e)}")

def cargar_punto_control() -> Dict[str, Any]:
    """Carga el último punto de control guardado."""
    ruta_checkpoint = 'config/checkpoint.json'
    
    # Estado por defecto (inicio de búsqueda)
    estado_defecto = {
        "activo": False,
        "comunidad_actual": "",
        "comunidad_idx": 0,
        "keyword_actual": "",
        "keyword_idx": 0,
        "ciudad_actual": "",
        "ciudad_idx": 0,
        "en_ciudad": False,
        "comunidades_completadas": [],
        "fecha_checkpoint": ""
    }
    
    if not os.path.exists(ruta_checkpoint):
        return estado_defecto
    
    try:
        with open(ruta_checkpoint, 'r', encoding='utf-8') as f:
            estado = json.load(f)
        
        logging.getLogger('Prospector').info(f"Punto de control cargado: {estado.get('comunidad_actual', 'N/A')}, {estado.get('keyword_actual', 'N/A')}")
        
        # Verificar si el checkpoint es válido y se marcó como activo
        if not estado.get("activo", False):
            return estado_defecto
            
        return estado
    except Exception as e:
        logging.getLogger('Prospector').error(f"Error al cargar punto de control: {str(e)}")
        return estado_defecto