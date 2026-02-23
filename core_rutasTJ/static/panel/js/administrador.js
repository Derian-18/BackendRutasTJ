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
document.getElementById("btn-terminar").onclick = function () {
    const nombre = document.getElementById("nombreRuta").value.trim();

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
    .then(res => {
        if (!res.ok) throw new Error('Error en la respuesta del servidor');
        return res.json();
    })
    .then(data => {
        if(data.error) {
            alert("Error: " + data.error);
        } else {
            alert("Ruta guardada correctamente");
            document.getElementById("nombreRuta").value = "";
            limpiarMapa();
            cargarRutas();
            cargarTablaRutas();
        }
    })
    .catch(err => console.error("Error al guardar:", err));
};

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
                tr.innerHTML = `
                    <td>${ruta.id}</td>
                    <td>${ruta.nombre}</td>
                    <td>
                        <button onclick="eliminarRuta(${ruta.id})">🗑️ Eliminar</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        });
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