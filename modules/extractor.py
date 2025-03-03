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
        
        # Lista de dominios comunes de bibliotecas y frameworks para exclusión
        self.exclusion_domains = [
            'jquery', 'js', 'cdn', 'npm', 'webpack', 'babel', 'typescript',
            'vue', 'react', 'angular', 'node', 'npm', 'yarn', 'gulp', 'grunt',
            'browserify', 'webpack', 'parcel', 'rollup', 'vite', 'esbuild',
            'eslint', 'prettier', 'stylelint', 'postcss', 'sass', 'less',
            'tailwind', 'bootstrap', 'foundation', 'material', 'semantic',
            'lodash', 'underscore', 'moment', 'luxon', 'dayjs', 'date-fns',
            'axios', 'fetch', 'superagent', 'request', 'got', 'ky', 'phin',
            'sequelize', 'mongoose', 'typeorm', 'prisma', 'knex', 'objection',
            'express', 'koa', 'hapi', 'fastify', 'nest', 'next', 'nuxt',
            'gatsby', 'sapper', 'svelte', 'ember', 'backbone', 'riot', 'aurelia',
            'sentry', 'bugsnag', 'rollbar', 'logrocket', 'datadog', 'newrelic',
            'cypress', 'jest', 'mocha', 'chai', 'karma', 'jasmine', 'ava',
            'storybook', 'styleguidist', 'docz', 'docsify', 'vuepress', 'docusaurus',
            'socket', 'ws', 'graphql', 'apollo', 'relay', 'urql', 'hasura',
            'admin', 'version', 'v1', 'v2', 'v3', 'v4', 'v5', 'spa', 'web',
            'frontend', 'backend', 'api', 'service', 'app', 'module', 'plugin'
        ]
        
        # Patrones de regex para email y teléfono
        self.email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        self.phone_pattern = r'(?:\+34|34)?[ -]?[6789]\d{8}|(?:\+34|34)?[ -]?[6789](?:[ -]?\d{2}){4}'
    
    def validar_email(self, email: str) -> bool:
        """
        Valida que un email parezca legítimo y no sea una referencia a biblioteca.
        
        Args:
            email: Dirección de correo a validar
            
        Returns:
            True si el email parece válido, False en caso contrario
        """
        if not email or '@' not in email:
            return False
        
        # Verificar longitud mínima y máxima
        if len(email) < 6 or len(email) > 254:
            return False
        
        # Extraer el dominio (parte después del @)
        dominio_parts = email.split('@')
        if len(dominio_parts) != 2:
            return False
            
        dominio = dominio_parts[1].lower()
        
        # Verificar si el dominio es un TLD válido
        if '.' not in dominio:
            return False
        
        # Verificar si es un dominio de biblioteca o framework
        nombre_dominio = dominio.split('.')[0]
        for exclusion in self.exclusion_domains:
            if exclusion == nombre_dominio or exclusion in nombre_dominio:
                return False
        
        # Verificar que el TLD tenga al menos 2 caracteres
        extension = dominio.split('.')[-1]
        if len(extension) < 2:
            return False
        
        # Verificar si el email tiene números de versión (típico en libs)
        usuario = dominio_parts[0].lower()
        if re.search(r'\d+\.\d+\.\d+', usuario) or re.search(r'v\d+', usuario):
            return False
            
        # Rechazar emails con nombres de usuario muy cortos (a@dominio.com)
        if len(usuario) < 2:
            return False
            
        return True
    
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
            
            # Buscar email
            email_matches = re.findall(self.email_pattern, visible_text)
            email_valido = False
            
            for email in email_matches:
                email_lower = email.lower()
                if self.validar_email(email_lower):
                    contacto['email'] = email_lower
                    email_valido = True
                    self.logger.info(f"Email válido encontrado: {email_lower}")
                    break
                else:
                    self.logger.debug(f"Email descartado: {email_lower}")
            
            if not email_valido and email_matches:
                self.logger.info(f"Se encontraron {len(email_matches)} posibles emails, pero ninguno pasó la validación")
            
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
            
            # Buscar email
            email_matches = re.findall(self.email_pattern, page_source)
            email_valido = False
            
            for email in email_matches:
                email_lower = email.lower()
                if self.validar_email(email_lower):
                    contacto['email'] = email_lower
                    email_valido = True
                    self.logger.info(f"Email válido encontrado: {email_lower}")
                    break
                else:
                    self.logger.debug(f"Email descartado: {email_lower}")
            
            if not email_valido and email_matches:
                self.logger.info(f"Se encontraron {len(email_matches)} posibles emails, pero ninguno pasó la validación")
            
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
        Extrae información de contacto usando el extractor más adecuado.
        
        Args:
            url: URL a procesar
            zona: Zona geográfica
            tipo_zona: Tipo de zona ('comunidad' o 'ciudad')
            keyword: Palabra clave que generó este resultado
            
        Returns:
            Diccionario con la información de contacto
        """
        if self.necesita_javascript(url):
            self.logger.info(f"Usando extractor dinámico para {url}")
            return self.dynamic_extractor.extraer_info(url, zona, tipo_zona, keyword)
        else:
            self.logger.info(f"Usando extractor estático para {url}")
            return self.static_extractor.extraer_info(url, zona, tipo_zona, keyword)