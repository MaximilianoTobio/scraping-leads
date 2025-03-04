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
        
        # Cargar configuración de filtros si existe
        self.filtros = config.get('filtros_busqueda', {})
        self.sector_activo = self.filtros.get('sector_activo', 'default')
    
    def _obtener_filtros_sector(self) -> Dict[str, List[str]]:
        """
        Obtiene los términos de inclusión y exclusión para el sector activo.
        
        Returns:
            Diccionario con términos de inclusión y exclusión
        """
        sectores = self.filtros.get('sectores', {})
        if self.sector_activo not in sectores:
            self.logger.warning(f"Sector '{self.sector_activo}' no encontrado, usando default")
            sector_config = sectores.get('default', {})
        else:
            sector_config = sectores.get(self.sector_activo, {})
            
        return {
            'inclusiones': sector_config.get('inclusiones', []),
            'exclusiones': sector_config.get('exclusiones', [])
        }
    
    def _construir_query_optimizada(self, keyword: str, region: str) -> str:
        """
        Construye una consulta optimizada con términos de inclusión y exclusión.
        
        Args:
            keyword: Palabra clave principal
            region: Región geográfica
            
        Returns:
            Consulta optimizada para la API de Google
        """
        filtros = self._obtener_filtros_sector()
        
        # Términos de inclusión (al menos uno debe estar presente)
        inclusion_terms = filtros['inclusiones']
        if inclusion_terms:
            inclusion_query = " OR ".join(inclusion_terms)
            inclusion_query = f"({inclusion_query})"
        else:
            inclusion_query = ""
        
        # Términos de exclusión (ninguno debe estar presente)
        exclusion_terms = filtros['exclusiones']
        exclusion_query = " ".join([f"-{term}" for term in exclusion_terms]) if exclusion_terms else ""
        
        # Construir consulta final
        query_parts = [keyword, region, inclusion_query, exclusion_query, "contacto site:.es"]
        query = " ".join(filter(None, query_parts))
        
        return query
    
    def buscar(self, keyword: str, region: str) -> List[str]:
        """
        Realiza una búsqueda en Google combinando keyword y región.
        
        Args:
            keyword: Palabra clave de búsqueda
            region: Región geográfica (comunidad o ciudad)
            
        Returns:
            Lista de URLs de resultados
        """
        query = self._construir_query_optimizada(keyword, region)
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