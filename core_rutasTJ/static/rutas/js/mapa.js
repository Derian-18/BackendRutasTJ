/* ================= CONFIGURACIÓN MAPA ================= */

const southWest = L.latLng(32.45, -117.15);
const northEast = L.latLng(32.60, -116.85);
const bounds    = L.latLngBounds(southWest, northEast);

const map = L.map('map', {
    center: [32.5255, -117.0335],
    zoom: 13,
    minZoom: 12,
    maxZoom: 18,
    maxBounds: bounds,
    maxBoundsViscosity: 1.0
});

// DESPUÉS — agrega el header con referrerPolicy
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    minZoom: 12,
    maxZoom: 18,
    attribution: '&copy; OpenStreetMap contributors',
    referrerPolicy: 'no-referrer-when-downgrade'
}).addTo(map);

map.fitBounds(bounds);

/* ================= VARIABLES GLOBALES ================= */
let puntos        = [];
let markers       = [];
let rutaActual    = null;
let circuloA      = null;
let circuloB      = null;
let lineaConexionA = null;
let lineaConexionB = null;

const ENDPOINTS = {
    obtener:  '/rutas/obtener-rutas-usuario/',
    calcular: '/rutas/calcular-ruta/',
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

/* ================= ICONOS PERSONALIZADOS ================= */
// Ahora usamos clases CSS definidas en styles.css
const iconoVerde = L.divIcon({
    className: 'custom-div-icon',
    html: `<div class="marker-pin marker-pin-green"></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24]
});

const iconoRojo = L.divIcon({
    className: 'custom-div-icon',
    html: `<div class="marker-pin marker-pin-red"></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24]
});

/* ================= CLICK MAPA ================= */
map.on('click', function(e) {
    if (puntos.length >= 2) {
        alert("Ya has seleccionado origen y destino. Haz clic en 'Limpiar' para reiniciar.");
        return;
    }

    const { lat, lng } = e.latlng;
    puntos.push([lat, lng]);

    const esOrigen = puntos.length === 1;
    const titulo   = esOrigen ? 'Punto A (Origen)' : 'Punto B (Destino)';
    const icono    = esOrigen ? iconoVerde : iconoRojo;

    const marker = L.marker([lat, lng], { title: titulo, icon: icono }).addTo(map);
    markers.push(marker);
});

/* ================= LIMPIAR ================= */
function limpiarMapa() {
    markers.forEach(m => map.removeLayer(m));
    markers = [];
    puntos  = [];

    capasRuta.forEach(capa => map.removeLayer(capa));
    capasRuta  = [];
    rutaActual = null;

    if (circuloA)       { map.removeLayer(circuloA);       circuloA       = null; }
    if (circuloB)       { map.removeLayer(circuloB);       circuloB       = null; }
    if (lineaConexionA) { map.removeLayer(lineaConexionA); lineaConexionA = null; }
    if (lineaConexionB) { map.removeLayer(lineaConexionB); lineaConexionB = null; }

    const panel = document.getElementById('itinerario');
    if (panel) panel.innerHTML = '';
}

/* ================= CALCULAR RUTA ================= */
function calcularRutaOptima() {
    if (puntos.length !== 2) {
        alert("Debes seleccionar Punto A y Punto B");
        return;
    }

    const [latA, lonA] = puntos[0];
    const [latB, lonB] = puntos[1];

    const btn = document.getElementById('btnCalcular');
    if (btn) {
        btn.disabled    = true;
        btn.textContent = 'Calculando...';
    }

    fetch(ENDPOINTS.calcular, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken
        },
        body: JSON.stringify({ latA, lonA, latB, lonB })
    })
    .then(res => res.json().then(data => ({ ok: res.ok, data })))
    .then(({ ok, data }) => {
        if (!ok) {
            alert(data.error || "No se pudo calcular la ruta");
            return;
        }
        if (!data.ruta_optima) {
            alert("No se encontró ruta");
            return;
        }
        dibujarRutaOptima(data.ruta_optima);
        dibujarRadiosYConexiones(data);
        mostrarItinerario(data);
    })
    .catch(err => {
        console.error("Error:", err);
        alert("Error de conexión al servidor");
    })
    .finally(() => {
        if (btn) {
            btn.disabled    = false;
            btn.textContent = 'Calcular ruta';
        }
    });
}

/* ================= DIBUJAR RUTA ================= */
// Capas de la ruta (puede ser más de una polyline)
let capasRuta = [];

function dibujarRutaOptima(ruta) {
    // Limpiar capas anteriores
    capasRuta.forEach(capa => map.removeLayer(capa));
    capasRuta = [];
    if (rutaActual) { map.removeLayer(rutaActual); rutaActual = null; }

    const paradas = ruta.filter(paso => paso.tipo === "parada");
    if (paradas.length === 0) return;

    // Dividir en segmentos: cada vez que cambia virtual/no-virtual
    // dibujamos una polyline distinta con su color
    let segmento = [paradas[0]];

    for (let i = 1; i < paradas.length; i++) {
        const actual = paradas[i];
        const anterior = paradas[i - 1];

        // Si el tipo de tramo cambia, cerramos el segmento y abrimos uno nuevo
        if (actual.virtual !== anterior.virtual) {
            dibujarSegmento(segmento, anterior.virtual);
            segmento = [anterior]; // el punto de unión pertenece a ambos segmentos
        }
        segmento.push(actual);
    }

    // Dibujar el último segmento
    if (segmento.length >= 1) {
        dibujarSegmento(segmento, segmento[segmento.length - 1].virtual);
    }

    // Ajustar zoom al conjunto de todas las capas
    const todasCoords = paradas.map(p => [p.latitud, p.longitud]);
    const bounds = L.latLngBounds(todasCoords);
    map.fitBounds(bounds);
}

function dibujarSegmento(paradas, esVirtual) {
    if (paradas.length < 2) return;
    const coords = paradas.map(p => [p.latitud, p.longitud]);
    const capa = L.polyline(coords, {
        color: esVirtual ? 'orange' : 'blue',
        weight: 6,
        dashArray: esVirtual ? '8,6' : null  // punteado para tramos a pie
    }).addTo(map);
    capasRuta.push(capa);
    rutaActual = capa; // mantener referencia a la última capa para compatibilidad
}

/* ================= DIBUJAR RADIOS Y CONEXIONES ================= */
function dibujarRadiosYConexiones(data) {
    if (circuloA)       { map.removeLayer(circuloA);       circuloA       = null; }
    if (circuloB)       { map.removeLayer(circuloB);       circuloB       = null; }
    if (lineaConexionA) { map.removeLayer(lineaConexionA); lineaConexionA = null; }
    if (lineaConexionB) { map.removeLayer(lineaConexionB); lineaConexionB = null; }

    const [latA, lonA] = puntos[0];
    const [latB, lonB] = puntos[1];

    const paradaInicio = data.origen;
    const paradaFin    = data.destino;

    circuloA = L.circle([latA, lonA], {
        radius: 500, // Aqui cambiamos el radio, solo es el color, no es la distancia que envia el backend
        color: 'green',
        fillOpacity: 0.07
    }).addTo(map);

    circuloB = L.circle([latB, lonB], {
        radius: 500, // Igual aqui. De momento el radio para buscar rutas es de 400, este es solo el css, el backend marcara otra medida (Modificar para que sea mas alta)
        color: 'red',
        fillOpacity: 0.07
    }).addTo(map);

    lineaConexionA = L.polyline([
        [latA, lonA],
        [paradaInicio.latitud, paradaInicio.longitud]
    ], { color: 'green', dashArray: '5,5', weight: 4 }).addTo(map);

    lineaConexionB = L.polyline([
        [paradaFin.latitud, paradaFin.longitud],
        [latB, lonB]
    ], { color: 'red', dashArray: '5,5', weight: 4 }).addTo(map);
}

/* ================= ITINERARIO CON CLASES CSS ================= */
function mostrarItinerario(data) {
    const panel = document.getElementById('itinerario');
    if (!panel) return;

    const transbordos = data.ruta_optima.filter(p => p.tipo === 'transbordo');

    let html = `
        <div class="itinerary-container">
            <h3 class="itinerary-header">
                <span>🗺️ Itinerario</span>
                <span class="itinerary-meta">
                    — ${data.total_paradas} paradas · ${transbordos.length} transbordo(s)
                </span>
            </h3>
            <div class="itinerary-steps">
    `;

    // Origen
    html += `
        <div class="itinerary-point">
            <span>🟢</span>
            <span><strong>Origen:</strong> ${data.origen.nombre}</span>
        </div>
    `;

    // Rutas y transbordos
    transbordos.forEach((t, i) => {
        html += `
            <div class="itinerary-transfer">
                <span>🚌</span>
                <span>
                    ${i === 0 ? '<strong>Tomar ruta:</strong>' : '<strong>Transbordo → tomar ruta:</strong>'}
                    <strong class="route-highlight"> ${t.ruta}</strong>
                </span>
            </div>
        `;
    });

    // Destino
    html += `
        <div class="itinerary-point">
            <span>🔴</span>
            <span><strong>Destino:</strong> ${data.destino.nombre}</span>
        </div>
    `;

    html += `</div></div>`;
    panel.innerHTML = html;
}

/* ================= CARGAR RUTAS ================= */
function cargarRutas() {
    fetch(ENDPOINTS.obtener)
        .then(res => {
            if (!res.ok) throw new Error('No se pudieron obtener las rutas');
            return res.json();
        })
        .then(rutas => {
            llenarSelect(rutas);
            llenarTabla(rutas);
        })
        .catch(err => console.error("Error al cargar rutas:", err));
}

function llenarSelect(rutas) {
    const select = document.getElementById('rutaSelect');
    if (!select) return;

    select.innerHTML = '<option value="">-- Selecciona una ruta --</option>';
    rutas.forEach(ruta => {
        const option = document.createElement('option');
        option.value = ruta.id;
        option.textContent = ruta.nombre;
        option.dataset.coordenadas = JSON.stringify(ruta.coordenadas);
        select.appendChild(option);
    });
}

function llenarTabla(rutas) {
    const tbody = document.getElementById('tablaRutas');
    if (!tbody) return;

    tbody.innerHTML = '';
    rutas.forEach(ruta => {
        const tr       = document.createElement('tr');
        const tdId     = document.createElement('td');
        const tdNombre = document.createElement('td');
        const tdAccion = document.createElement('td');

        tdId.textContent     = ruta.id;
        tdNombre.textContent = ruta.nombre;

        const btn = document.createElement('button');
        btn.textContent   = '👁️ Ver en Mapa';
        btn.classList.add('btn-view-map'); // Usamos clase en lugar de cssText
        btn.addEventListener('click', () => mostrarRuta(ruta.coordenadas));

        tdAccion.appendChild(btn);
        tr.appendChild(tdId);
        tr.appendChild(tdNombre);
        tr.appendChild(tdAccion);
        tbody.appendChild(tr);
    });
}

function mostrarRuta(coordenadas) {
    capasRuta.forEach(capa => map.removeLayer(capa));
    capasRuta = [];
    rutaActual = null;

    if (!coordenadas || coordenadas.length === 0) return;

    rutaActual = L.polyline(coordenadas, { color: 'blue', weight: 5 }).addTo(map);
    capasRuta.push(rutaActual);
    map.fitBounds(rutaActual.getBounds());
}

/* ================= SELECT LISTENER ================= */
const selectElement = document.getElementById('rutaSelect');
if (selectElement) {
    selectElement.addEventListener('change', function () {
        const option = this.options[this.selectedIndex];
        if (!option.value || !option.dataset.coordenadas) return;
        mostrarRuta(JSON.parse(option.dataset.coordenadas));
    });
}

/* ================= CARGA INICIAL ================= */
cargarRutas();