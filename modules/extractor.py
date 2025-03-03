import re
import time
import random
import logging
import requests
from typing import Dict, Any, Optional, Union
from bs4 import BeautifulSoup
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.robotparser import RobotFileParser

class BaseExtractor:
    """Clase base para extractores de información de contacto."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el extractor base.
        
        Args:
            config: Configuración del sistema
        """
        self.config = config
        self.logger = logging.getLogger('Extractor')
        self.delay_range = config['delays']['entre_extracciones']
        
        # Patrones de regex para email y teléfono
        self.email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        self.phone_pattern = r'(?:\+34|34)?[ -]?[6789]\d{8}|(?:\+34|34)?[ -]?[6789](?:[ -]?\d{2}){4}'
    
    def _verificar_robots_txt(self, url: str) -> bool:
        """
        Verifica si el scraping está permitido según robots.txt.
        
        Args:
            url: URL del sitio a verificar
            
        Returns:
            True si está permitido, False si no
        """
        try:
            # Extraer dominio base
            parts = url.split('/')
            base_url = f"{parts[0]}//{parts[2]}"
            robots_url = f"{base_url}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            return rp.can_fetch("*", url)
        except Exception as e:
            self.logger.warning(f"No se pudo verificar robots.txt para {url}: {str(e)}")
            return True  # Asumir permitido en caso de error
    
    def normalizar_telefono(self, telefono: str) -> str:
        """
        Normaliza un número de teléfono al formato +34XXXXXXXXX.
        
        Args:
            telefono: Número de teléfono en cualquier formato
            
        Returns:
            Teléfono normalizado
        """
        if not telefono:
            return ""
            
        # Eliminar espacios, guiones y otros caracteres no numéricos
        telefono_limpio = re.sub(r'[^0-9+]', '', telefono)
        
        # Asegurar que tenga prefijo +34
        if not telefono_limpio.startswith('+'):
            if telefono_limpio.startswith('34'):
                telefono_limpio = '+' + telefono_limpio
            else:
                telefono_limpio = '+34' + telefono_limpio
                
        return telefono_limpio
    
    def generar_link_whatsapp(self, telefono: str) -> Optional[str]:
        """
        Genera un enlace de WhatsApp para contacto directo.
        
        Args:
            telefono: Número de teléfono normalizado
            
        Returns:
            URL de WhatsApp o None si no hay teléfono
        """
        if not telefono:
            return None
            
        telefono_limpio = telefono.replace('+34', '').replace(' ', '').replace('-', '')
        mensaje = quote("mensaje a enviar... ")
        return f"https://wa.me/34{telefono_limpio}?text={mensaje}"
    
    def extraer_info(self, url: str, zona: str, tipo_zona: str, keyword: str) -> Dict[str, Any]:
        """
        Método abstracto para extraer información de contacto.
        Debe ser implementado por subclases.
        """
        raise NotImplementedError("Las subclases deben implementar extraer_info")


class StaticExtractor(BaseExtractor):
    """Extractor para páginas estáticas usando requests y BeautifulSoup."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Rotación de User Agents para evitar bloqueos
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]
        # Variable para almacenar el último texto visible
        self.ultimo_texto_visible = ""
    
    def _get_random_headers(self) -> Dict[str, str]:
        """Genera headers aleatorios para simular navegador real."""
        user_agent = random.choice(self.user_agents)
        return {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
    
    def extraer_info(self, url: str, zona: str, tipo_zona: str, keyword: str) -> Dict[str, Any]:
        """
        Extrae información de contacto de una página estática.
        
        Args:
            url: URL de la página a extraer
            zona: Nombre de la zona (comunidad o ciudad)
            tipo_zona: Tipo de zona ('comunidad' o 'ciudad')
            keyword: Palabra clave que generó este resultado
            
        Returns:
            Diccionario con la información de contacto extraída
        """
        contacto = {
            'url': url,
            'zona': zona,
            'tipo_zona': tipo_zona,
            'keyword': keyword
        }
        
        # Verificar permiso de robots.txt
        if not self._verificar_robots_txt(url):
            self.logger.info(f"Scraping no permitido según robots.txt para {url}")
            return contacto
        
        try:
            headers = self._get_random_headers()
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                self.logger.warning(f"Error {response.status_code} al acceder a {url}")
                return contacto
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer todo el texto visible de la página
            visible_text = soup.get_text()
            
            # Guardar texto visible para evaluación posterior
            self.ultimo_texto_visible = visible_text
            
            # Buscar email
            email_matches = re.findall(self.email_pattern, visible_text)
            if email_matches:
                contacto['email'] = email_matches[0].lower()
            
            # Buscar teléfono
            phone_matches = re.findall(self.phone_pattern, visible_text)
            if phone_matches:
                telefono_normalizado = self.normalizar_telefono(phone_matches[0])
                contacto['telefono'] = telefono_normalizado
                contacto['whatsapp_link'] = self.generar_link_whatsapp(telefono_normalizado)
            
            # Extraer título como nombre
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.text.strip()
                contacto['nombre'] = title.split('|')[0].strip()
            else:
                contacto['nombre'] = url.split('/')[2]
            
            # Añadir timestamp
            from datetime import datetime
            contacto['fecha_extraccion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.logger.info(f"Información extraída de {url}")
            
            # Delay para evitar sobrecarga
            time.sleep(random.uniform(self.delay_range[0], self.delay_range[1]))
            
            return contacto
            
        except Exception as e:
            self.logger.error(f"Error al extraer información de {url}: {str(e)}")
            return contacto


class DynamicExtractor(BaseExtractor):
    """Extractor para páginas que requieren JavaScript usando Selenium."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.driver = None
        self.setup_driver()
        # Variable para almacenar el último texto visible
        self.ultimo_texto_visible = ""
    
    def setup_driver(self):
        """Configura el navegador Chrome con opciones para evitar detección."""
        chrome_options = Options()
        
        if self.config['selenium']['headless']:
            chrome_options.add_argument('--headless')
            
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            self.driver.implicitly_wait(self.config['selenium']['timeout'])
            self.wait = WebDriverWait(self.driver, self.config['selenium']['timeout'])
            self.logger.info("Driver de Selenium configurado exitosamente")
        except Exception as e:
            self.logger.error(f"Error al configurar el driver de Selenium: {str(e)}")
            raise
    
    def extraer_info(self, url: str, zona: str, tipo_zona: str, keyword: str) -> Dict[str, Any]:
        """
        Extrae información de contacto de una página dinámica con JavaScript.
        
        Args:
            url: URL de la página a extraer
            zona: Nombre de la zona (comunidad o ciudad)
            tipo_zona: Tipo de zona ('comunidad' o 'ciudad')
            keyword: Palabra clave que generó este resultado
            
        Returns:
            Diccionario con la información de contacto extraída
        """
        contacto = {
            'url': url,
            'zona': zona,
            'tipo_zona': tipo_zona,
            'keyword': keyword
        }
        
        # Verificar permiso de robots.txt
        if not self._verificar_robots_txt(url):
            self.logger.info(f"Scraping no permitido según robots.txt para {url}")
            return contacto
        
        try:
            self.driver.get(url)
            
            # Esperar a que la página cargue completamente
            time.sleep(random.uniform(1, 3))
            
            # Obtener contenido de la página
            page_source = self.driver.page_source
            
            # Extraer texto visible
            soup = BeautifulSoup(page_source, 'html.parser')
            visible_text = soup.get_text()
            
            # Guardar texto visible para evaluación posterior
            self.ultimo_texto_visible = visible_text
            
            # Buscar email
            email_matches = re.findall(self.email_pattern, page_source)
            if email_matches:
                contacto['email'] = email_matches[0].lower()
            
            # Buscar teléfono
            phone_matches = re.findall(self.phone_pattern, page_source)
            if phone_matches:
                for phone in phone_matches:
                    telefono_normalizado = self.normalizar_telefono(phone)
                    if telefono_normalizado:
                        contacto['telefono'] = telefono_normalizado
                        contacto['whatsapp_link'] = self.generar_link_whatsapp(telefono_normalizado)
                        break
            
            # Extraer título como nombre
            try:
                title = self.driver.title
                contacto['nombre'] = title.split('|')[0].strip()
            except:
                contacto['nombre'] = url.split('/')[2]
            
            # Añadir timestamp
            from datetime import datetime
            contacto['fecha_extraccion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.logger.info(f"Información extraída de {url} usando Selenium")
            
            # Delay para evitar sobrecarga
            time.sleep(random.uniform(self.delay_range[0], self.delay_range[1]))
            
            return contacto
            
        except Exception as e:
            self.logger.error(f"Error al extraer información de {url} con Selenium: {str(e)}")
            return contacto
    
    def __del__(self):
        """Cierra el driver al destruir la instancia."""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("Driver de Selenium cerrado correctamente")
        except Exception as e:
            self.logger.error(f"Error al cerrar el driver de Selenium: {str(e)}")


class EvaluadorRelevancia:
    """
    Evalúa la relevancia de una página web para determinar si corresponde
    a un potencial revendedor según la configuración del sector.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el evaluador con la configuración de filtros.
        
        Args:
            config: Configuración del sistema
        """
        self.logger = logging.getLogger('EvaluadorRelevancia')
        self.filtros = config.get('filtros_busqueda', {})
        self.sector_activo = self.filtros.get('sector_activo', 'default')
        self.config = config
    
    def _obtener_terminos_relevancia(self) -> Dict[str, List[str]]:
        """
        Obtiene los términos de relevancia del sector activo.
        
        Returns:
            Diccionario con términos relevantes e irrelevantes
        """
        sectores = self.filtros.get('sectores', {})
        if self.sector_activo not in sectores:
            self.logger.warning(f"Sector '{self.sector_activo}' no encontrado, usando default")
            sector_config = sectores.get('default', {})
        else:
            sector_config = sectores.get(self.sector_activo, {})
            
        return {
            'relevantes': sector_config.get('terminos_relevantes', []),
            'irrelevantes': sector_config.get('terminos_irrelevantes', [])
        }
    
    def evaluar_pagina(self, texto: str, titulo: str) -> Dict[str, Any]:
        """
        Evalúa si una página corresponde a un revendedor potencial.
        
        Args:
            texto: Texto completo de la página
            titulo: Título de la página
            
        Returns:
            Dict con resultado de evaluación, score y razón
        """
        terminos = self._obtener_terminos_relevancia()
        texto_lower = texto.lower()
        titulo_lower = titulo.lower() if titulo else ""
        
        # Contar términos relevantes (doble peso para los que aparecen en el título)
        relevantes_encontrados = sum(1 for term in terminos['relevantes'] if term in texto_lower)
        relevantes_en_titulo = sum(2 for term in terminos['relevantes'] if term in titulo_lower)
        
        # Contar términos irrelevantes
        irrelevantes_encontrados = sum(1 for term in terminos['irrelevantes'] if term in texto_lower)
        
        # Calcular puntuación
        puntuacion_total = relevantes_encontrados + relevantes_en_titulo - irrelevantes_encontrados
        
        # Normalizar puntuación (0-100)
        max_posible = len(terminos['relevantes']) * 3  # texto + doble en título
        puntuacion_normalizada = min(100, max(0, (puntuacion_total / max(1, max_posible)) * 100))
        
        # Evaluar resultado
        umbral = 40  # Umbral configurable
        es_relevante = puntuacion_normalizada >= umbral
        
        # Determinar razón
        if puntuacion_normalizada >= 70:
            razon = "Alta relevancia: probable revendedor"
        elif puntuacion_normalizada >= umbral:
            razon = "Relevancia media: posible revendedor"
        else:
            razon = "Baja relevancia: probablemente no es revendedor"
        
        return {
            'es_relevante': es_relevante,
            'puntuacion': puntuacion_normalizada,
            'razon': razon,
            'relevantes_encontrados': relevantes_encontrados,
            'irrelevantes_encontrados': irrelevantes_encontrados
        }


class ExtractorSelector:
    """
    Clase para seleccionar el extractor más adecuado para cada URL.
    Implementa un sistema híbrido que elige entre extractores estáticos y dinámicos.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el selector de extractores.
        
        Args:
            config: Configuración del sistema
        """
        self.static_extractor = StaticExtractor(config)
        self.dynamic_extractor = DynamicExtractor(config)
        self.logger = logging.getLogger('ExtractorSelector')
        self.config = config
        
        # Añadir evaluador de relevancia
        self.evaluador = EvaluadorRelevancia(config)
        
        # Dominios que sabemos que requieren JavaScript
        self.js_required_domains = [
            # Agregar aquí dominios conocidos que requieren JS
            'infoempresa.com', 'facebook.com', 'instagram.com', 'linkedin.com',
            'twitter.com', 'einforma.com', 'empresite.eleconomista.es',
            'guiaempresas.universia.es', 'expansion.com', 'axesor.es'
        ]
    
    def necesita_javascript(self, url: str) -> bool:
        """
        Determina de manera robusta si una URL probablemente necesita JavaScript para cargar contenido.
        
        Args:
            url: URL a evaluar
            
        Returns:
            True si probablemente necesita JS, False en caso contrario
        """
        # 1. Verificar lista de dominios conocidos
        for dominio in self.js_required_domains:
            if dominio in url:
                return True
        
        # 2. Realizar análisis preliminar
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            r = requests.get(url, headers=headers, timeout=5)
            
            if r.status_code != 200:
                # Si hay problemas para acceder, usar Selenium por seguridad
                return True
                
            html = r.text.lower()
            
            # 3. Buscar frameworks y bibliotecas JavaScript
            js_frameworks = [
                'vue', 'react', 'angular', 'jquery', 'next.js', 'nuxt', 
                'typescript', 'svelte', 'meteor', 'ember'
            ]
            
            for framework in js_frameworks:
                if framework in html:
                    self.logger.info(f"Detectado framework {framework} en {url}")
                    return True
            
            # 4. Buscar indicadores de interactividad JavaScript
            js_indicators = [
                # JavaScript para mostrar datos dinámicamente
                'onclick=', 'onmouseover=', 'document.write', 'document.getElementById',
                '.innerHTML', 'fetch(', 'axios.', '.ajax', '.post(', '.get(',
                
                # Protección de contactos
                'data-email', 'data-tel', 'protected-email', 'decode(', 'unveil(', 
                'reveal', 'protected-content', 'data-cfemail',
                
                # Frameworks generales
                'app.js', 'bundle.js', 'main.js',
                
                # Carga diferida
                'lazy-load', 'lazy-src', 'data-src', 'loading="lazy"',
                
                # SPA (Single Page Applications)
                'router-view', 'router-link', 'ng-view', 'data-route'
            ]
            
            for indicator in js_indicators:
                if indicator in html:
                    self.logger.info(f"Detectado indicador JS '{indicator}' en {url}")
                    return True
                    
            # 5. Verificar ocultamiento de correos y teléfonos
            # Buscar patrones que sugieren que los contactos están protegidos
            soup = BeautifulSoup(html, 'html.parser')
            
            # Patrones comunes de protección
            if len(soup.select('span[data-email]')) > 0 or len(soup.select('[data-tel]')) > 0:
                return True
                
            # Verificar si existen elementos que parecen contactos pero están codificados o vacíos
            contact_patterns = [
                '[email protected]', 'email-protected', 'contact@', 'info@',
                'span.email', 'div.email', '.contact-email', '.contact-phone'
            ]
            
            for pattern in contact_patterns:
                if pattern in html or soup.select(pattern):
                    return True
            
            # 6. Verificar la ausencia de información de contacto visible
            # Si no hay teléfonos ni correos visibles, probablemente estén ocultos con JS
            email_regex = r'[\w\.-]+@[\w\.-]+\.\w+'
            phone_regex = r'(?:\+34|34)?[ -]?[6789]\d{2}[ -]?\d{2}[ -]?\d{2}[ -]?\d{2}'
            
            emails_found = re.findall(email_regex, html)
            phones_found = re.findall(phone_regex, html)
            
            # Si hay mucho contenido pero no hay contactos visibles, probablemente necesite JS
            if len(html) > 10000 and not emails_found and not phones_found:
                self.logger.info(f"Página grande sin contactos visibles en {url}, probablemente necesite JS")
                return True
            
            # Si parece ser una página de contacto pero no hay información visible, usar JS
            if 'contacto' in url.lower() or 'contact' in url.lower():
                if not emails_found and not phones_found:
                    return True
            
            # Default: si pasó todas las verificaciones, probablemente no necesite JS
            return False
            
        except Exception as e:
            self.logger.warning(f"Error al analizar {url}, usando Selenium por precaución: {str(e)}")
            # En caso de error, usar Selenium por seguridad
            return True
    
    def extraer_informacion(self, url: str, zona: str, tipo_zona: str, keyword: str) -> Dict[str, Any]:
        """
        Extrae información de contacto usando el extractor más adecuado
        y evalúa la relevancia del contenido.
        
        Args:
            url: URL a procesar
            zona: Zona geográfica
            tipo_zona: Tipo de zona ('comunidad' o 'ciudad')
            keyword: Palabra clave que generó este resultado
            
        Returns:
            Diccionario con la información de contacto
        """
        # Determinar qué extractor usar
        if self.necesita_javascript(url):
            self.logger.info(f"Usando extractor dinámico para {url}")
            contacto = self.dynamic_extractor.extraer_info(url, zona, tipo_zona, keyword)
        else:
            self.logger.info(f"Usando extractor estático para {url}")
            contacto = self.static_extractor.extraer_info(url, zona, tipo_zona, keyword)
        
        # Si se obtuvo contenido visible, evaluar relevancia
        if contacto and ('nombre' in contacto or 'url' in contacto):
            # Obtener texto visible (simulado aquí, en una implementación real 
            # sería el texto completo del sitio)
            texto_visible = ""
            titulo = contacto.get('nombre', '')
            
            # Para el extractor estático
            if hasattr(self.static_extractor, 'ultimo_texto_visible'):
                texto_visible = self.static_extractor.ultimo_texto_visible
            
            # Para el extractor dinámico
            elif hasattr(self.dynamic_extractor, 'ultimo_texto_visible'):
                texto_visible = self.dynamic_extractor.ultimo_texto_visible
            
            # Evaluar relevancia solo si hay suficiente texto
            if len(texto_visible) > 100 or titulo:
                evaluacion = self.evaluador.evaluar_pagina(texto_visible, titulo)
                
                # Agregar información de relevancia al contacto
                contacto['relevancia'] = evaluacion['puntuacion']
                contacto['es_relevante'] = evaluacion['es_relevante']
                contacto['razon_relevancia'] = evaluacion['razon']
                
                # Informar resultado
                self.logger.info(f"Evaluación de relevancia para {url}: {evaluacion['puntuacion']}% - {evaluacion['razon']}")
        
        return contacto