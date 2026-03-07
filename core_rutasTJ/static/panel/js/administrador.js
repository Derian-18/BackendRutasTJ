/* ================= CONFIGURACIÓN MAPA ================= */

const southWest = L.latLng(32.45, -117.15);
const northEast = L.latLng(32.60, -116.85);
const bounds = L.latLngBounds(southWest, northEast);

const map = L.map('map', {
    center: [32.5255, -117.0335],
    zoom: 13,
    minZoom: 12,
    maxZoom: 18,
    maxBounds: bounds,
    maxBoundsViscosity: 1.0
});

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    minZoom: 12,
    maxZoom: 18
}).addTo(map);

map.fitBounds(bounds);

/* ================= VARIABLES GLOBALES ================= */
let puntos = [];
let markers = [];
let rutaActual = null;

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

/* ================= EVENTOS DE CLICK ================= */
map.on('click', function(e) {
    const { lat, lng } = e.latlng;
    puntos.push([lat, lng]);

    const marker = L.marker([lat, lng]).addTo(map);
    markers.push(marker);
});

function limpiarMapa() {
    markers.forEach(m => map.removeLayer(m));
    markers = [];
    puntos = [];
    if (rutaActual) map.removeLayer(rutaActual);
}

/* ================= GUARDAR RUTA ================= */
const btnTerminar = document.getElementById("btn-terminar");
if (btnTerminar) {
    btnTerminar.onclick = function () {
        const nombreInput = document.getElementById("nombreRuta");
        const nombre = nombreInput.value.trim();

        if (!nombre || puntos.length < 2) {
            alert("Escribe un nombre y marca al menos 2 puntos en el mapa");
            return;
        }

        fetch(ENDPOINTS.guardar, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken 
            },
            body: JSON.stringify({
                nombre: nombre,
                coordenadas: puntos 
            })
        })
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                alert("Error: " + data.error);
            } else {
                alert("Ruta guardada correctamente");
                nombreInput.value = "";
                limpiarMapa();
                cargarRutas();
                cargarTablaRutas();
            }
        })
        .catch(err => console.error("Error al guardar:", err));
    };
}

/* ================= CARGAR Y MOSTRAR ================= */
function cargarRutas() {
    fetch(ENDPOINTS.obtener)
        .then(res => res.json())
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

/* ================= TABLA Y ELIMINACIÓN ================= */
function cargarTablaRutas() {
    fetch(ENDPOINTS.obtener)
        .then(res => res.json())
        .then(rutas => {
            const tbody = document.getElementById('tablaRutas');
            if(!tbody) return;
            tbody.innerHTML = '';

            rutas.forEach(ruta => {
                const tr = document.createElement('tr');
                
                // Usamos clases CSS en lugar de style inline
                tr.innerHTML = `
                    <td>${ruta.id}</td>
                    <td>${ruta.nombre}</td>
                    <td>
                        <button class="btn-action btn-view" data-id="${ruta.id}">
                            👁️ Ver en Mapa
                        </button>
                        <button class="btn-action btn-delete" data-id="${ruta.id}">
                            🗑️ Eliminar
                        </button>
                    </td>
                `;

                // Asignamos los eventos de forma limpia
                const btnView = tr.querySelector('.btn-view');
                btnView.onclick = () => mostrarRuta(ruta.coordenadas);

                const btnDel = tr.querySelector('.btn-delete');
                btnDel.onclick = () => eliminarRuta(ruta.id);

                tbody.appendChild(tr);
            });
        })
        .catch(err => console.error("Error al llenar la tabla:", err));
}

function eliminarRuta(rutaId) {
    if (!confirm("¿Seguro que deseas eliminar esta ruta?")) return;

    fetch(ENDPOINTS.eliminar(rutaId), {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrftoken }
    })
    .then(res => res.json())
    .then(() => {
        cargarTablaRutas();
        cargarRutas();
        if (rutaActual) map.removeLayer(rutaActual);
    })
    .catch(err => console.error("Error al eliminar:", err));
}

// Carga Inicial
cargarRutas();
cargarTablaRutas();

// Listener del Select
const selectElement = document.getElementById('rutaSelect');
if(selectElement) {
    selectElement.addEventListener('change', function () {
        const option = this.options[this.selectedIndex];
        if (!option.value || !option.dataset.coordenadas) return;
        mostrarRuta(JSON.parse(option.dataset.coordenadas));
    });
}