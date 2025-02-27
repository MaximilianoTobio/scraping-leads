# Sistema de Prospección CBD

Un sistema modular para la prospección automatizada de negocios CBD en España, optimizado para eficiencia, escalabilidad y cumplimiento legal.

## Descripción General

Este sistema permite identificar y extraer información de contacto (correos electrónicos y teléfonos) de negocios relacionados con productos CBD y naturales en diferentes regiones de España. El sistema realiza búsquedas combinando palabras clave con ubicaciones geográficas, extrae datos de contacto de los sitios web encontrados, y guarda los resultados en formatos CSV y JSON.

La arquitectura ha sido completamente rediseñada siguiendo las mejores prácticas de desarrollo y las recomendaciones del informe técnico para optimizar rendimiento, eficiencia y cumplimiento legal.

## Características Principales

- **Búsquedas mediante Google Custom Search API**: Utiliza la API oficial en lugar de scraping directo, garantizando cumplimiento con términos de servicio y mayor eficiencia.
- **Sistema híbrido de extracción**: Utiliza BeautifulSoup para páginas estáticas y Selenium solo cuando es necesario, optimizando recursos.
- **Gestión eficiente de duplicados**: Evita contactos repetidos mediante estructuras de datos optimizadas.
- **Diseño modular**: Separa responsabilidades en componentes especializados para mejor mantenimiento y escalabilidad.
- **Configuración externalizada**: Permite modificar parámetros sin alterar el código.
- **Técnicas anti-bloqueo**: Implementa rotación de User-Agents, respeto de robots.txt y delays inteligentes.
- **Cumplimiento legal**: Opera dentro de marcos legales aplicables en España para web scraping.

## Estructura del Proyecto

```
prospeccion_cbd/
├── config/
│   ├── config.json         # Configuración principal (API keys, etc.)
│   ├── keywords.json       # Palabras clave para búsqueda
│   └── regiones.json       # Comunidades y ciudades
├── modules/
│   ├── buscador.py         # Módulo de búsqueda (Google API)
│   ├── extractor.py        # Extracción de datos de contacto
│   ├── gestor_datos.py     # Gestión de datos y eliminación de duplicados
│   └── utils.py            # Funciones auxiliares
├── logs/                   # Directorio para archivos de log
├── results/                # Directorio para resultados
├── main.py                 # Script principal
└── requirements.txt        # Dependencias
```

## Requisitos Previos

Antes de utilizar el sistema, necesitas:

1. **Cuenta de Google Cloud Platform**:
   - Tener un proyecto activo
   - Activar la API de Custom Search
   - Generar una clave API

2. **Motor de Búsqueda Personalizado**:
   - Crear un motor en [Programmable Search Engine](https://programmablesearchengine.google.com/)
   - Obtener el ID de búsqueda (CX)

3. **Python 3.7+** con pip instalado

## Instalación

1. Clonar o descargar este repositorio:
   ```bash
   git clone [url-repositorio]
   cd prospeccion_cbd
   ```

2. Instalar las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Crear la estructura de directorios (si no existe):
   ```bash
   mkdir -p config logs results
   ```

4. Configurar los archivos JSON (ver sección de Configuración)

## Configuración

### 1. Configuración Principal (config/config.json)

```json
{
  "google_api": {
    "api_key": "TU_API_KEY",
    "cx_id": "TU_CX_ID",
    "resultados_por_busqueda": 5
  },
  "selenium": {
    "headless": true,
    "timeout": 10
  },
  "delays": {
    "entre_busquedas": [3, 6],
    "entre_extracciones": [1, 3]
  },
  "modo_prueba": true,
  "logs": {
    "level": "INFO",
    "rotation": true
  },
  "guardado": {
    "intervalo": 300
  }
}
```

### 2. Palabras Clave (config/keywords.json)

```json
[
  "herbolario",
  "tienda natural",
  "CBD",
  "productos naturales",
  "tienda holística",
  "tienda ecológica", 
  "herboristería",
  "aceite CBD"
]
```

### 3. Regiones (config/regiones.json)

```json
{
  "comunidades": [
    "Andalucía", "Aragón", "Asturias", "Baleares", "Canarias",
    "Cantabria", "Castilla y León", "Castilla-La Mancha", "Cataluña",
    "Comunidad Valenciana", "Extremadura", "Galicia", "Madrid",
    "Murcia", "Navarra", "País Vasco", "La Rioja"
  ],
  "ciudades": {
    "Andalucía": ["Sevilla", "Málaga", "Córdoba", "Granada", "Almería", "Jaén", "Cádiz", "Huelva", "Marbella", "Dos Hermanas", "Algeciras"],
    "Aragón": ["Zaragoza", "Huesca", "Teruel"],
    "Asturias": ["Oviedo", "Gijón", "Avilés"],
    "Baleares": ["Palma", "Ibiza", "Manacor", "Mahón"],
    "Canarias": ["Las Palmas", "Santa Cruz de Tenerife", "La Laguna", "Arona"],
    "Cantabria": ["Santander", "Torrelavega"],
    "Castilla y León": ["Valladolid", "Burgos", "Salamanca", "León", "Zamora", "Ávila", "Segovia", "Soria", "Palencia"],
    "Castilla-La Mancha": ["Toledo", "Albacete", "Ciudad Real", "Cuenca", "Guadalajara"],
    "Cataluña": ["Barcelona", "Tarragona", "Lleida", "Girona", "Sabadell", "Terrassa", "Badalona"],
    "Comunidad Valenciana": ["Valencia", "Alicante", "Castellón", "Elche", "Torrevieja"],
    "Extremadura": ["Mérida", "Badajoz", "Cáceres"],
    "Galicia": ["Santiago de Compostela", "A Coruña", "Vigo", "Ourense", "Lugo", "Pontevedra"],
    "Madrid": ["Madrid", "Móstoles", "Alcalá de Henares", "Fuenlabrada", "Leganés", "Getafe"],
    "Murcia": ["Murcia", "Cartagena", "Lorca"],
    "Navarra": ["Pamplona", "Tudela"],
    "País Vasco": ["Bilbao", "San Sebastián", "Vitoria"],
    "La Rioja": ["Logroño"]
  }
}
```

## Uso

### Modo Prueba

Para verificar el funcionamiento con una muestra reducida:

```bash
python main.py
```

Con la configuración predeterminada (`"modo_prueba": true`), el sistema utilizará solo:
- Las 2 primeras palabras clave
- Las 2 primeras comunidades autónomas
- Las 2 primeras ciudades de cada comunidad

### Ejecución Completa

Para realizar una búsqueda completa:

1. Editar `config.json` y establecer `"modo_prueba": false`
2. Ejecutar:
   ```bash
   python main.py
   ```

## Componentes del Sistema

### 1. Buscador (Google API)

El módulo `buscador.py` implementa:
- Búsqueda mediante Google Custom Search API
- Construcción óptima de consultas
- Control de ritmo para respetar límites de la API
- Registro detallado de operaciones
- Manejo de errores y excepciones

### 2. Sistema de Extracción

El módulo `extractor.py` incluye:

- **ExtractorSelector**: Elige el método más adecuado para cada URL
- **StaticExtractor**: Usa BeautifulSoup para páginas HTML estáticas
- **DynamicExtractor**: Usa Selenium para páginas que requieren JavaScript
- Verificación de robots.txt
- Normalización de datos (emails y teléfonos)
- Técnicas anti-bloqueo
- Generación de enlaces para WhatsApp

### 3. Gestor de Datos

El módulo `gestor_datos.py` gestiona:
- Detección eficiente de duplicados
- Normalización de formatos
- Guardado periódico y final
- Exportación a CSV y JSON
- Estadísticas de resultados

## Funcionamiento en Detalle

1. **Inicialización**:
   - Carga de configuración
   - Inicialización de componentes
   - Configuración de logging

2. **Proceso de Búsqueda**:
   - Iteración por comunidades autónomas y palabras clave
   - Búsqueda mediante Google API
   - Obtención de URLs de resultados

3. **Extracción de Datos**:
   - Selección de método de extracción para cada URL
   - Petición y análisis de páginas web
   - Extracción de emails, teléfonos y nombres

4. **Gestión de Resultados**:
   - Filtrado de duplicados
   - Normalización de datos
   - Guardado periódico en CSV y JSON
   - Generación de estadísticas

## Optimizaciones Implementadas

Este sistema ha sido optimizado siguiendo las recomendaciones del informe técnico:

1. **Uso de APIs oficiales** en lugar de scraping directo:
   - Mayor eficiencia y rendimiento
   - Cumplimiento de términos de servicio
   - Reducción de riesgos de bloqueo

2. **Reducción del uso de Selenium**:
   - Menor consumo de recursos
   - Mayor velocidad de procesamiento
   - Enfoque híbrido para máxima efectividad

3. **Técnicas anti-bloqueo mejoradas**:
   - Rotación de User-Agents
   - Respeto de robots.txt
   - Delays inteligentes
   - Headers realistas

4. **Estructura modular**:
   - Separación de responsabilidades
   - Fácil mantenimiento y extensión
   - Mayor testabilidad

5. **Gestión eficiente de datos**:
   - Estructuras optimizadas para detección de duplicados
   - Normalización consistente
   - Guardado incremental

## Personalización Avanzada

### Configuración de Proxies

Para implementar rotación de proxies, modificar `StaticExtractor` en `extractor.py`:

```python
def __init__(self, config):
    super().__init__(config)
    self.proxies = [
        "http://usuario:contraseña@proxy1:puerto",
        "http://usuario:contraseña@proxy2:puerto"
    ]
    
def _get_proxy(self):
    return random.choice(self.proxies)
    
def extraer_info(self, url, zona, tipo_zona, keyword):
    # ... código existente ...
    try:
        proxy = self._get_proxy()
        response = requests.get(
            url, 
            headers=self._get_random_headers(),
            proxies={"http": proxy, "https": proxy},
            timeout=10
        )
        # ... resto del código ...
```

### Detección de JavaScript

Para mejorar la detección de páginas que requieren JavaScript:

```python
# En ExtractorSelector, añadir o modificar:
def necesita_javascript(self, url):
    # Lista de dominios conocidos que usan JS para mostrar contactos
    for dominio in self.js_required_domains:
        if dominio in url:
            return True
            
    # Intentar análisis preliminar
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            # Buscar indicadores de contenido dinámico
            js_indicators = [
                'vue.js', 'react', 'angular', 
                'onclick=', 'data-react', 
                'loadContact', 'showEmail'
            ]
            for indicator in js_indicators:
                if indicator in r.text.lower():
                    return True
        return False
    except:
        # En caso de error, usar Selenium por seguridad
        return True
```

## Consideraciones Legales

El sistema ha sido diseñado para operar respetando:

1. **Términos de Servicio**: Usa APIs oficiales para búsquedas, evitando scraping directo de Google.

2. **Políticas robots.txt**: Verifica y respeta directivas de robots.txt de cada sitio.

3. **Ritmo de peticiones**: Implementa delays y limita la frecuencia para evitar sobrecarga de servidores.

4. **Protección de Datos**: Opera bajo el principio de recopilar solo información de contacto pública para fines comerciales B2B.

5. **Cumplimiento RGPD**: Al usar los datos para marketing, recuerda proporcionar formas de darse de baja y usar el interés legítimo como base legal para contactos B2B.

## Solución de Problemas

### Límites de la API de Google

Google Custom Search API tiene un límite de 100 consultas gratuitas por día. Si recibes errores de cuota:

1. Distribuir la ejecución en varios días
2. Considerar la versión de pago de la API
3. Guardar parcialmente resultados y continuar al día siguiente

### Problemas con Selenium

Si Selenium falla:

1. Verificar versión de Chrome y chromedriver
2. Probar sin modo headless para diagnosticar
3. Verificar las opciones anti-detección

### Errores de Extracción

Si la extracción de datos no funciona como se espera:

1. Revisar los patrones regex para email y teléfono
2. Verificar si las páginas usan técnicas anti-scraping
3. Comprobar la estructura HTML de la página (puede cambiar)

## Mantenimiento

Para mantener el sistema actualizado:

1. Revisar periódicamente las dependencias
2. Actualizar patrones de extracción si cambian los formatos
3. Ampliar lista `js_required_domains` con sitios problemáticos descubiertos
4. Ajustar tiempos de espera según experiencia

## Créditos y Licencia

Este sistema fue desarrollado siguiendo el análisis y recomendaciones de optimización para el script de prospección original. 

Licencia: MIT
