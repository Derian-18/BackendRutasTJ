/* ================= CONFIGURACIÓN MAPA ================= */
const map = L.map('map').setView([32.5255, -117.0335], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
}).addTo(map);

/* ================= VARIABLES GLOBALES ================= */
let puntos = [];
let markers = [];
let rutaActual = null;

// Rutas configuradas manualmente (Ajusta según tu urls.py si es necesario)
const ENDPOINTS = {
    guardar: '/panel/guardar-ruta/',
    obtener: '/panel/obtener-rutas/',
    eliminar: (id) => `/panel/eliminar-ruta/${id}/`
};

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

/* ================= CLICK MAPA (PUNTO A y PUNTO B) ================= */
map.on('click', function(e) {
    // Si ya tenemos 2 puntos, no permitir más clics
    if (puntos.length >= 2) {
        alert("Ya has seleccionado origen y destino. Haz clic en 'Limpiar' para reiniciar.");
        return;
    }

    const { lat, lng } = e.latlng;
    puntos.push([lat, lng]);

    // Diferenciar colores: Verde para Inicio (A), Rojo para Fin (B)
    const colorMarker = (puntos.length === 1) ? 'green' : 'red';
    const titulo = (puntos.length === 1) ? 'Punto A (Origen)' : 'Punto B (Destino)';

    // Crear un marcador simple con color (usando filtros CSS para no cargar iconos extra)
    const marker = L.marker([lat, lng], { title: titulo }).addTo(map);
    
    // Aplicar un estilo rápido al icono para diferenciarlos
    if (puntos.length === 1) {
        marker._icon.style.filter = "hue-rotate(120deg)"; // Verde
    } else {
        marker._icon.style.filter = "hue-rotate(0deg)";   // Rojo (estándar)
    }

    markers.push(marker);
});

function limpiarMapa() {
    markers.forEach(m => map.removeLayer(m));
    markers = [];
    puntos = [];
    if (rutaActual) map.removeLayer(rutaActual);
}

/* ================= CARGAR Y MOSTRAR ================= */
function cargarRutas() {
    fetch(ENDPOINTS.obtener)
        .then(res => {
            if (!res.ok) throw new Error('No se pudieron obtener las rutas');
            return res.json();
        })
        .then(rutas => {
            const select = document.getElementById('rutaSelect');
            if(!select) return;
            
            select.innerHTML = '<option value="">-- Selecciona una ruta --</option>';

            rutas.forEach(ruta => {
                const option = document.createElement('option');
                option.value = ruta.id;
                option.textContent = ruta.nombre;
                option.dataset.coordenadas = JSON.stringify(ruta.coordenadas);
                select.appendChild(option);
            });
        })
        .catch(err => console.error("Error al cargar select:", err));
}

function mostrarRuta(coordenadas) {
    if (rutaActual) map.removeLayer(rutaActual);
    if (!coordenadas || coordenadas.length === 0) return;

    rutaActual = L.polyline(coordenadas, {
        color: 'blue',
        weight: 5
    }).addTo(map);

    map.fitBounds(rutaActual.getBounds());
}

const selectElement = document.getElementById('rutaSelect');
if(selectElement) {
    selectElement.addEventListener('change', function () {
        const option = this.options[this.selectedIndex];
        if (!option.value || !option.dataset.coordenadas) return;
        mostrarRuta(JSON.parse(option.dataset.coordenadas));
    });
}

/* ================= TABLA Y ACCIONES ================= */

function cargarTablaRutas() {
    fetch(ENDPOINTS.obtener)
        .then(res => {
            if (!res.ok) throw new Error('Error al obtener rutas');
            return res.json();
        })
        .then(rutas => {
            const tbody = document.getElementById('tablaRutas');
            if(!tbody) return;
            tbody.innerHTML = '';

            rutas.forEach(ruta => {
                const tr = document.createElement('tr');
                
                // Convertimos las coordenadas a string para pasarlas al botón
                const coordsStr = JSON.stringify(ruta.coordenadas);

                tr.innerHTML = `
                    <td>${ruta.id}</td>
                    <td>${ruta.nombre}</td>
                    <td>
                        <button onclick='mostrarRuta(${coordsStr})' style="background-color: #e1f5fe; cursor: pointer;">
                            👁️ Ver en Mapa
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error("Error al llenar la tabla:", err));
}

// Carga Inicial
cargarRutas();
cargarTablaRutas();