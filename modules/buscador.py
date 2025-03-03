import requests
import time
import random
import logging
from urllib.parse import quote
from typing import List, Dict, Any

class GoogleBuscador:
    """
    Módulo de búsqueda utilizando Google Custom Search API.
    Reemplaza las búsquedas con Selenium para mayor eficiencia y cumplimiento.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el buscador con la configuración necesaria.
        
        Args:
            config: Configuración que incluye claves API y parámetros.
        """
        self.api_key = config['google_api']['api_key']
        self.cx_id = config['google_api']['cx_id']
        self.resultados_max = config['google_api']['resultados_por_busqueda']
        self.delay_range = config['delays']['entre_busquedas']
        self.logger = logging.getLogger('Buscador')
        self.base_url = "https://customsearch.googleapis.com/customsearch/v1"
    
    def buscar(self, keyword: str, region: str) -> List[str]:
        """
        Realiza una búsqueda en Google combinando keyword y región.
        
        Args:
            keyword: Palabra clave de búsqueda
            region: Región geográfica (comunidad o ciudad)
            
        Returns:
            Lista de URLs de resultados
        """
        query = f"{keyword} {region} contacto site:.es"
        self.logger.info(f"Buscando: '{query}'")
        
        params = {
            "key": self.api_key,
            "cx": self.cx_id,
            "q": query,
            "num": 10  # Máximo permitido por la API
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            urls = []
            
            if 'items' in data:
                for item in data['items']:
                    if len(urls) >= self.resultados_max:
                        break
                    urls.append(item['link'])
                
            self.logger.info(f"Encontrados {len(urls)} resultados para '{keyword}' en '{region}'")
            
            # Delay para evitar sobrecargar la API
            time.sleep(random.uniform(self.delay_range[0], self.delay_range[1]))
            
            return urls
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error en la búsqueda de Google para '{keyword}' en '{region}': {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error inesperado en búsqueda: {str(e)}")
            return []