#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Set

# Importar módulos personalizados
from modules.utils import (cargar_configuracion, setup_logging, filtrar_parametros_prueba, 
                          gestionar_contador_busquedas, actualizar_contador_busquedas,
                          guardar_punto_control, cargar_punto_control)
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
        
        # Variables de estado para seguimiento de progreso
        self.comunidad_actual = ""
        self.comunidad_idx = 0
        self.keyword_actual = ""
        self.keyword_idx = 0
        self.ciudad_actual = ""
        self.ciudad_idx = 0
        self.en_ciudad = False
        self.comunidades_completadas = set()
        
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
    
    def actualizar_estado(self, comunidad="", comunidad_idx=None, keyword="", keyword_idx=None, 
                          ciudad="", ciudad_idx=None, en_ciudad=None):
        """Actualiza las variables de estado de la búsqueda."""
        if comunidad:
            self.comunidad_actual = comunidad
        if comunidad_idx is not None:
            self.comunidad_idx = comunidad_idx
        if keyword:
            self.keyword_actual = keyword
        if keyword_idx is not None:
            self.keyword_idx = keyword_idx
        if ciudad:
            self.ciudad_actual = ciudad
        if ciudad_idx is not None:
            self.ciudad_idx = ciudad_idx
        if en_ciudad is not None:
            self.en_ciudad = en_ciudad
    
    def ejecutar_busqueda(self):
        """
        Ejecuta el proceso completo de búsqueda y extracción con soporte para continuar
        desde el último punto de control si se alcanzó el límite diario.
        """
        # Extraer parámetros de configuración
        keywords = self.config['keywords']
        comunidades = self.config['regiones']['comunidades']
        ciudades = self.config['regiones']['ciudades']
        
        # Obtener el límite de búsquedas diarias
        limite_busquedas = self.config.get('limite_busquedas_diarias', 95)
        self.logger.info(f"Límite de búsquedas diarias configurado a: {limite_busquedas}")
        
        # Inicializar contador de búsquedas persistente
        contador_busquedas, fecha_actual = gestionar_contador_busquedas()
        self.logger.info(f"Estado actual: {contador_busquedas}/{limite_busquedas} búsquedas realizadas hoy ({fecha_actual})")
        
        # Cargar punto de control si existe
        checkpoint = cargar_punto_control()
        
        # Determinar índices de inicio basados en el checkpoint
        comunidad_inicio_idx = checkpoint["comunidad_idx"] if checkpoint["activo"] else 0
        keyword_inicio_idx = checkpoint["keyword_idx"] if checkpoint["activo"] else 0
        
        # Verificar si comenzamos desde una ciudad
        en_ciudad = checkpoint["en_ciudad"] if checkpoint["activo"] else False
        ciudad_inicio_idx = checkpoint["ciudad_idx"] if checkpoint["activo"] else 0
        
        # Marcar comunidades ya completadas
        self.comunidades_completadas = set(checkpoint["comunidades_completadas"]) if checkpoint["activo"] else set()
        
        if checkpoint["activo"]:
            self.logger.info(f"Continuando desde el último punto de control: " 
                           f"Comunidad {checkpoint['comunidad_actual']}, "
                           f"Keyword {checkpoint['keyword_actual']}")
            if en_ciudad:
                self.logger.info(f"Continuando en ciudad: {checkpoint['ciudad_actual']}")
        
        # Actualizar estado
        self.actualizar_estado(
            comunidad=checkpoint["comunidad_actual"],
            comunidad_idx=comunidad_inicio_idx,
            keyword=checkpoint["keyword_actual"],
            keyword_idx=keyword_inicio_idx,
            ciudad=checkpoint["ciudad_actual"],
            ciudad_idx=ciudad_inicio_idx,
            en_ciudad=en_ciudad
        )
        
        # Verificar si ya se alcanzó el límite antes de empezar
        if contador_busquedas >= limite_busquedas:
            self.logger.warning(f"Ya se ha alcanzado el límite diario de {limite_busquedas} búsquedas. No se realizarán más búsquedas hoy.")
            
            # Guardar resultados y mostrar estadísticas
            self.gestor_datos.guardar_resultados()
            stats = self.gestor_datos.obtener_estadisticas()
            stats['busquedas_realizadas'] = contador_busquedas
            stats['limite_busquedas'] = limite_busquedas
            
            return stats
        
        # 1. Búsqueda a nivel de Comunidad Autónoma
        for comunidad_idx, comunidad in enumerate(comunidades[comunidad_inicio_idx:], start=comunidad_inicio_idx):
            # Actualizar estado
            self.actualizar_estado(comunidad=comunidad, comunidad_idx=comunidad_idx)
            
            # Saltar comunidades completadas
            if comunidad in self.comunidades_completadas:
                self.logger.info(f"Saltando comunidad ya procesada: {comunidad}")
                continue
                
            self.logger.info(f"Iniciando búsqueda en la Comunidad: {comunidad}")
            
            # Para la primera comunidad, usar keyword_inicio_idx, para el resto empezar desde 0
            k_inicio = keyword_inicio_idx if comunidad_idx == comunidad_inicio_idx else 0
            
            for keyword_idx, keyword in enumerate(keywords[k_inicio:], start=k_inicio):
                # Actualizar estado
                self.actualizar_estado(keyword=keyword, keyword_idx=keyword_idx)
                
                # Verificar límite de búsquedas
                if contador_busquedas >= limite_busquedas:
                    self.logger.warning(f"Se ha alcanzado el límite diario de {limite_busquedas} búsquedas. Guardando punto de control.")
                    
                    # Guardar punto de control para continuar mañana
                    checkpoint_data = {
                        "activo": True,
                        "comunidad_actual": comunidad,
                        "comunidad_idx": comunidad_idx,
                        "keyword_actual": keyword,
                        "keyword_idx": keyword_idx,
                        "ciudad_actual": "",
                        "ciudad_idx": 0,
                        "en_ciudad": False,
                        "comunidades_completadas": list(self.comunidades_completadas),
                        "fecha_checkpoint": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    guardar_punto_control(checkpoint_data)
                    break
                
                contador_busquedas += 1
                self.logger.info(f"Buscando '{keyword}' en '{comunidad}' - Búsquedas: {contador_busquedas}/{limite_busquedas}")
                
                # Obtener URLs y procesar resultados
                urls = self.buscador.buscar(keyword, comunidad)
                for url in urls:
                    contacto = self.extractor.extraer_informacion(
                        url=url,
                        zona=comunidad,
                        tipo_zona='comunidad',
                        keyword=keyword
                    )
                    self.gestor_datos.agregar_contacto(contacto)
                
                # Actualizar el contador persistente después de cada búsqueda
                actualizar_contador_busquedas(contador_busquedas, fecha_actual)
            
            # Verificar si llegamos al límite
            if contador_busquedas >= limite_busquedas:
                break
                
            # 2. Búsqueda específica en ciudades de la comunidad
            if comunidad in ciudades:
                # Si estamos continuando en una comunidad específica y se marcó para continuar en ciudad
                c_inicio = ciudad_inicio_idx if (comunidad_idx == comunidad_inicio_idx and en_ciudad) else 0
                
                for ciudad_idx, ciudad in enumerate(ciudades[comunidad][c_inicio:], start=c_inicio):
                    # Actualizar estado
                    self.actualizar_estado(ciudad=ciudad, ciudad_idx=ciudad_idx, en_ciudad=True)
                    
                    self.logger.info(f"Buscando en ciudad: {ciudad} ({comunidad})")
                    
                    # Para la primera ciudad cuando se continúa, usar keyword_inicio_idx
                    kw_inicio = keyword_inicio_idx if (comunidad_idx == comunidad_inicio_idx and 
                                                   ciudad_idx == c_inicio and en_ciudad) else 0
                    
                    for keyword_idx, keyword in enumerate(keywords[kw_inicio:], start=kw_inicio):
                        # Actualizar estado
                        self.actualizar_estado(keyword=keyword, keyword_idx=keyword_idx)
                        
                        # Verificar límite de búsquedas
                        if contador_busquedas >= limite_busquedas:
                            # Guardar punto de control para continuar en esta ciudad
                            checkpoint_data = {
                                "activo": True,
                                "comunidad_actual": comunidad,
                                "comunidad_idx": comunidad_idx,
                                "keyword_actual": keyword,
                                "keyword_idx": keyword_idx,
                                "ciudad_actual": ciudad,
                                "ciudad_idx": ciudad_idx,
                                "en_ciudad": True,
                                "comunidades_completadas": list(self.comunidades_completadas),
                                "fecha_checkpoint": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            guardar_punto_control(checkpoint_data)
                            break
                        
                        contador_busquedas += 1
                        self.logger.info(f"Buscando '{keyword}' en '{ciudad}' - Búsquedas: {contador_busquedas}/{limite_busquedas}")
                        
                        # Proceso de búsqueda y extracción
                        urls = self.buscador.buscar(keyword, ciudad)
                        for url in urls:
                            contacto = self.extractor.extraer_informacion(
                                url=url,
                                zona=ciudad,
                                tipo_zona='ciudad',
                                keyword=keyword
                            )
                            self.gestor_datos.agregar_contacto(contacto)
                        
                        # Actualizar contador persistente
                        actualizar_contador_busquedas(contador_busquedas, fecha_actual)
                    
                    # Verificar límite después de cada ciudad
                    if contador_busquedas >= limite_busquedas:
                        break
                
                # Verificar límite después de todas las ciudades de la comunidad
                if contador_busquedas >= limite_busquedas:
                    break
            
            # Marcar esta comunidad como completada
            self.comunidades_completadas.add(comunidad)
            
            # Actualizar checkpoint para indicar que esta comunidad está completada
            checkpoint_data = {
                "activo": True,
                "comunidad_actual": "",
                "comunidad_idx": comunidad_idx + 1,  # La próxima comunidad
                "keyword_actual": "",
                "keyword_idx": 0,
                "ciudad_actual": "",
                "ciudad_idx": 0,
                "en_ciudad": False,
                "comunidades_completadas": list(self.comunidades_completadas),
                "fecha_checkpoint": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            guardar_punto_control(checkpoint_data)
        
        # Al finalizar todas las comunidades, resetear el checkpoint
        checkpoint_data = {
            "activo": False,
            "comunidad_actual": "",
            "comunidad_idx": 0,
            "keyword_actual": "",
            "keyword_idx": 0,
            "ciudad_actual": "",
            "ciudad_idx": 0,
            "en_ciudad": False,
            "comunidades_completadas": [],
            "fecha_checkpoint": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        guardar_punto_control(checkpoint_data)
        
        # Guardar resultados finales
        self.gestor_datos.guardar_resultados()
        
        # Mostrar estadísticas
        stats = self.gestor_datos.obtener_estadisticas()
        stats['busquedas_realizadas'] = contador_busquedas
        stats['limite_busquedas'] = limite_busquedas
        
        return stats

def main():
    """Función principal para ejecutar el script."""
    prospector = None
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
        if prospector is not None:
            print("Guardando punto de control y resultados...")
            
            # Guardar resultados
            prospector.gestor_datos.guardar_resultados()
            
            # Guardar punto de control
            checkpoint_data = {
                "activo": True,
                "comunidad_actual": prospector.comunidad_actual,
                "comunidad_idx": prospector.comunidad_idx,
                "keyword_actual": prospector.keyword_actual,
                "keyword_idx": prospector.keyword_idx,
                "ciudad_actual": prospector.ciudad_actual,
                "ciudad_idx": prospector.ciudad_idx,
                "en_ciudad": prospector.en_ciudad,
                "comunidades_completadas": list(prospector.comunidades_completadas),
                "fecha_checkpoint": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            guardar_punto_control(checkpoint_data)
            
            # Mostrar estadísticas
            try:
                stats = prospector.gestor_datos.obtener_estadisticas()
                print(f"Se han guardado {stats['total_contactos']} contactos")
            except Exception as e:
                print(f"Error al obtener estadísticas: {str(e)}")
                
        sys.exit(0)
    except Exception as e:
        print(f"\nError inesperado: {str(e)}")
        # También intentar guardar progreso en caso de error
        if prospector is not None:
            try:
                print("Guardando resultados parciales y punto de control...")
                prospector.gestor_datos.guardar_resultados()
                
                # Guardar punto de control
                checkpoint_data = {
                    "activo": True,
                    "comunidad_actual": prospector.comunidad_actual,
                    "comunidad_idx": prospector.comunidad_idx,
                    "keyword_actual": prospector.keyword_actual,
                    "keyword_idx": prospector.keyword_idx,
                    "ciudad_actual": prospector.ciudad_actual,
                    "ciudad_idx": prospector.ciudad_idx,
                    "en_ciudad": prospector.en_ciudad,
                    "comunidades_completadas": list(prospector.comunidades_completadas),
                    "fecha_checkpoint": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                guardar_punto_control(checkpoint_data)
            except Exception as ex:
                print(f"Error al guardar progreso: {str(ex)}")
        sys.exit(1)

if __name__ == "__main__":
    main()