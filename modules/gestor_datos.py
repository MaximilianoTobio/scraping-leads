import json
import pandas as pd
import logging
from typing import List, Dict, Any, Set
from datetime import datetime

class GestorDatos:
    """
    Gestiona el almacenamiento, eliminación de duplicados y exportación de datos.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el gestor de datos.
        
        Args:
            config: Configuración del sistema
        """
        self.config = config
        self.logger = logging.getLogger('GestorDatos')
        self.contactos = []
        self.urls_vistas = set()
        self.telefonos_vistos = set()
        self.ultimo_guardado = datetime.now()
        self.intervalo_guardado = config['guardado']['intervalo']  # segundos
    
    def agregar_contacto(self, contacto: Dict[str, Any]) -> bool:
        """
        Agrega un contacto si no es duplicado.
        
        Args:
            contacto: Diccionario con datos de contacto
            
        Returns:
            True si se agregó, False si era duplicado
        """
        url = contacto.get('url')
        telefono = contacto.get('telefono')
        
        # Verificar si ya tenemos este contacto
        if url in self.urls_vistas:
            return False
            
        if telefono and telefono in self.telefonos_vistos:
            return False
        
        # Agregar a las colecciones
        self.contactos.append(contacto)
        self.urls_vistas.add(url)
        if telefono:
            self.telefonos_vistos.add(telefono)
            
        self.logger.info(f"Contacto agregado: {url}")
        
        # Verificar si es momento de guardar
        delta = (datetime.now() - self.ultimo_guardado).total_seconds()
        if delta >= self.intervalo_guardado:
            self.guardar_resultados()
            self.ultimo_guardado = datetime.now()
            
        return True
    
    def agregar_multiples_contactos(self, nuevos_contactos: List[Dict[str, Any]]) -> int:
        """
        Agrega múltiples contactos, filtrando duplicados.
        
        Args:
            nuevos_contactos: Lista de contactos a agregar
            
        Returns:
            Número de contactos agregados
        """
        contador = 0
        for contacto in nuevos_contactos:
            if self.agregar_contacto(contacto):
                contador += 1
                
        return contador
    
    def eliminar_duplicados(self) -> None:
        """Elimina contactos duplicados basándose en URL y teléfono."""
        contactos_unicos = []
        urls_vistas = set()
        telefonos_vistos = set()
        
        for contacto in self.contactos:
            url = contacto.get('url')
            telefono = contacto.get('telefono')
            
            if url not in urls_vistas and (not telefono or telefono not in telefonos_vistos):
                contactos_unicos.append(contacto)
                urls_vistas.add(url)
                if telefono:
                    telefonos_vistos.add(telefono)
        
        self.contactos = contactos_unicos
        self.urls_vistas = urls_vistas
        self.telefonos_vistos = telefonos_vistos
        
        self.logger.info(f"Duplicados eliminados. Contactos únicos: {len(self.contactos)}")
    
    def guardar_resultados(self) -> None:
        """Guarda los resultados en archivos CSV y JSON."""
        if not self.contactos:
            self.logger.warning("No hay contactos para guardar")
            return
            
        # Primero eliminar posibles duplicados
        self.eliminar_duplicados()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Guardar en CSV
        df = pd.DataFrame(self.contactos)
        csv_filename = f'resultados_cbd_{timestamp}.csv'
        df.to_csv(csv_filename, index=False)
        
        # Guardar en JSON
        json_filename = f'resultados_cbd_{timestamp}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.contactos, f, ensure_ascii=False, indent=4)
        
        self.logger.info(f"Resultados guardados en {csv_filename} y {json_filename}")
    
    def obtener_estadisticas(self) -> Dict[str, int]:
        """
        Obtiene estadísticas sobre los contactos recopilados.
        
        Returns:
            Diccionario con estadísticas
        """
        return {
            "total_contactos": len(self.contactos),
            "con_email": sum(1 for c in self.contactos if 'email' in c and c['email']),
            "con_telefono": sum(1 for c in self.contactos if 'telefono' in c and c['telefono']),
            "comunidades": len(set(c['zona'] for c in self.contactos if c['tipo_zona'] == 'comunidad')),
            "ciudades": len(set(c['zona'] for c in self.contactos if c['tipo_zona'] == 'ciudad'))
        }