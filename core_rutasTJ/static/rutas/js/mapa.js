/* ================= CONFIGURACIÓN MAPA ================= */

const southWest = L.latLng(32.35, -117.20);
const northEast = L.latLng(32.55, -116.70);
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
let capasRuta = [];

function dibujarRutaOptima(ruta) {
    capasRuta.forEach(capa => map.removeLayer(capa));
    capasRuta = [];
    if (rutaActual) { map.removeLayer(rutaActual); rutaActual = null; }

    const paradas = ruta.filter(paso => paso.tipo === "parada");
    if (paradas.length === 0) return;

    let segmento = [paradas[0]];

    for (let i = 1; i < paradas.length; i++) {
        const actual = paradas[i];
        const anterior = paradas[i - 1];

        if (actual.virtual !== anterior.virtual) {
            dibujarSegmento(segmento, anterior.virtual);
            segmento = [anterior];
        }
        segmento.push(actual);
    }

    if (segmento.length >= 1) {
        dibujarSegmento(segmento, segmento[segmento.length - 1].virtual);
    }

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
        dashArray: esVirtual ? '8,6' : null
    }).addTo(map);
    capasRuta.push(capa);
    rutaActual = capa;
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
        radius: 500,
        color: 'green',
        fillOpacity: 0.07
    }).addTo(map);

    circuloB = L.circle([latB, lonB], {
        radius: 500,
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

/* ================= ITINERARIO ================= */
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

    html += `
        <div class="itinerary-point">
            <span>🟢</span>
            <span><strong>Origen:</strong> ${data.origen.nombre}</span>
        </div>
    `;

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
        const tdNombre = document.createElement('td');

        tdNombre.textContent = ruta.nombre;
        tdNombre.classList.add('ruta-clickable');
        tdNombre.addEventListener('click', () => mostrarRuta(ruta.coordenadas));

        tr.appendChild(tdNombre);
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