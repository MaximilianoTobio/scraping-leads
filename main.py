#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

# Importar módulos personalizados
from modules.utils import cargar_configuracion, setup_logging, filtrar_parametros_prueba
from modules.buscador import GoogleBuscador
from modules.extractor import ExtractorSelector
from modules.gestor_datos import GestorDatos

class Prospector:
    """
    Clase principal que coordina el proceso de prospección de negocios.
    Implementa un diseño modular que separa responsabilidades.
    """
    
    def __init__(self):
        """Inicializa el prospector y sus componentes."""
        # Asegurar que existan los directorios necesarios
        os.makedirs('config', exist_ok=True)
        os.makedirs('results', exist_ok=True)
        
        # Configurar logging
        self.logger = setup_logging()
        self.logger.info("Iniciando Prospector con estructura modular...")
        
        try:
            # Cargar configuración
            self.config = cargar_configuracion()
            
            # Ajustar configuración si estamos en modo prueba
            if self.config.get('modo_prueba', False):
                self.config = filtrar_parametros_prueba(self.config)
                self.logger.info("Ejecutando en MODO PRUEBA con parámetros limitados")
            
            # Inicializar componentes
            self.buscador = GoogleBuscador(self.config)
            self.extractor = ExtractorSelector(self.config)
            self.gestor_datos = GestorDatos(self.config)
            
            self.logger.info("Sistema inicializado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error durante la inicialización: {str(e)}")
            sys.exit(1)
    
    def ejecutar_busqueda(self):
        """
        Ejecuta el proceso completo de búsqueda y extracción.
        Se organiza en comunidades y ciudades, similar al original.
        Implementa un límite diario de búsquedas para evitar exceder
        las restricciones de la API.
        """
        # Extraer parámetros de configuración
        keywords = self.config['keywords']
        comunidades = self.config['regiones']['comunidades']
        ciudades = self.config['regiones']['ciudades']
        
        # Obtener el límite de búsquedas diarias de la configuración
        limite_busquedas = self.config.get('limite_busquedas_diarias', 95)
        self.logger.info(f"Límite de búsquedas diarias configurado a: {limite_busquedas}")
        
        # Inicializar contador de búsquedas
        contador_busquedas = 0
        
        # Calcular total de búsquedas para mostrar progreso
        total_busquedas_comunidad = len(comunidades) * len(keywords)
        busquedas_realizadas = 0
        
        # 1. Búsqueda a nivel de Comunidad Autónoma
        for comunidad in comunidades:
            self.logger.info(f"Iniciando búsqueda en la Comunidad: {comunidad}")
            
            for keyword in keywords:
                # Verificar si hemos alcanzado el límite de búsquedas
                if contador_busquedas >= limite_busquedas:
                    self.logger.warning(f"Se ha alcanzado el límite diario de {limite_busquedas} búsquedas. Deteniendo el proceso.")
                    break
                
                busquedas_realizadas += 1
                contador_busquedas += 1
                
                progreso = (busquedas_realizadas / total_busquedas_comunidad) * 100
                self.logger.info(f"Progreso: {progreso:.2f}% - Buscando '{keyword}' en '{comunidad}' - Búsquedas: {contador_busquedas}/{limite_busquedas}")
                
                # Obtener URLs de resultados
                urls = self.buscador.buscar(keyword, comunidad)
                
                # Procesar cada resultado
                for url in urls:
                    # Extraer información de contacto
                    contacto = self.extractor.extraer_informacion(
                        url=url,
                        zona=comunidad,
                        tipo_zona='comunidad',
                        keyword=keyword
                    )
                    
                    # Agregar al gestor de datos (filtra duplicados automáticamente)
                    self.gestor_datos.agregar_contacto(contacto)
            
            # Verificar nuevamente si hemos alcanzado el límite
            if contador_busquedas >= limite_busquedas:
                break
                
            # 2. Búsqueda específica en ciudades principales de la comunidad
            if comunidad in ciudades:
                for ciudad in ciudades[comunidad]:
                    self.logger.info(f"Buscando en ciudad: {ciudad} ({comunidad})")
                    
                    for keyword in keywords:
                        # Verificar si hemos alcanzado el límite de búsquedas
                        if contador_busquedas >= limite_busquedas:
                            self.logger.warning(f"Se ha alcanzado el límite diario de {limite_busquedas} búsquedas. Deteniendo el proceso.")
                            break
                        
                        contador_busquedas += 1
                        self.logger.info(f"Buscando '{keyword}' en '{ciudad}' - Búsquedas: {contador_busquedas}/{limite_busquedas}")
                        
                        # Obtener URLs de resultados
                        urls = self.buscador.buscar(keyword, ciudad)
                        
                        # Procesar cada resultado
                        for url in urls:
                            # Extraer información de contacto
                            contacto = self.extractor.extraer_informacion(
                                url=url,
                                zona=ciudad,
                                tipo_zona='ciudad',
                                keyword=keyword
                            )
                            
                            # Agregar al gestor de datos
                            self.gestor_datos.agregar_contacto(contacto)
                    
                    # Verificar nuevamente si hemos alcanzado el límite
                    if contador_busquedas >= limite_busquedas:
                        break
                
                # Verificar si hemos alcanzado el límite después del bucle de ciudades
                if contador_busquedas >= limite_busquedas:
                    break
        
        # Guardar resultados finales
        self.gestor_datos.guardar_resultados()
        
        # Mostrar estadísticas
        stats = self.gestor_datos.obtener_estadisticas()
        self.logger.info("Búsqueda completada:")
        self.logger.info(f"Total de búsquedas realizadas: {contador_busquedas}/{limite_busquedas}")
        self.logger.info(f"Total de contactos encontrados: {stats['total_contactos']}")
        self.logger.info(f"Contactos con email: {stats['con_email']}")
        self.logger.info(f"Contactos con teléfono: {stats['con_telefono']}")
        
        # Añadir estadística de búsquedas a la respuesta
        stats['busquedas_realizadas'] = contador_busquedas
        stats['limite_busquedas'] = limite_busquedas
        
        return stats

def main():
    """Función principal para ejecutar el script."""
    try:
        # Crear y ejecutar el prospector
        prospector = Prospector()
        stats = prospector.ejecutar_busqueda()
        
        # Mostrar resumen en consola
        print("\nBúsqueda completada:")
        print(f"Total de contactos encontrados: {stats['total_contactos']}")
        print(f"Contactos con email: {stats['con_email']}")
        print(f"Contactos con teléfono: {stats['con_telefono']}")
        print(f"Búsquedas realizadas: {stats['busquedas_realizadas']}/{stats['limite_busquedas']}")
        
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\nError inesperado: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()