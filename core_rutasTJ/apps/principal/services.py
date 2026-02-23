from .models import Ruta, Conexion

def obtener_rutas_data():
    rutas = Ruta.objects.all()
    data = []

    for ruta in rutas:
        # Obtenemos las conexiones de esta ruta ordenadas
        # Nota: Esto asume que las conexiones siguen el orden de creación
        conexiones = Conexion.objects.filter(ruta=ruta).select_related('origen', 'destino')
        
        coordenadas = []
        if conexiones.exists():
            # Añadimos el origen de la primera conexión
            primera = conexiones.first()
            coordenadas.append([primera.origen.latitud, primera.origen.longitud])
            
            # Añadimos los destinos de todas las conexiones para formar la línea
            for conexion in conexiones:
                coordenadas.append([conexion.destino.latitud, conexion.destino.longitud])

        data.append({
            "id": ruta.id,
            "nombre": ruta.nombre,
            "coordenadas": coordenadas,  # Esto es lo que Leaflet necesita para L.polyline
            "paradas": [
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "lat": p.latitud,
                    "lng": p.longitud
                } for p in ruta.paradas.all()
            ]
        })

    return data