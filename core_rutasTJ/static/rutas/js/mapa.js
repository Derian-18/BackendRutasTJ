//* ================= CONFIGURACIÓN MAPA ================= */

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

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    minZoom: 12,
    maxZoom: 18
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
    className: '',
    html: `<div style="
        width: 24px; height: 24px;
        background: #22c55e;
        border: 3px solid #fff;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    "></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 24],
    popupAnchor: [0, -24]
});

const iconoRojo = L.divIcon({
    className: '',
    html: `<div style="
        width: 24px; height: 24px;
        background: #ef4444;
        border: 3px solid #fff;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    "></div>`,
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

    if (rutaActual)     { map.removeLayer(rutaActual);     rutaActual     = null; }
    if (circuloA)       { map.removeLayer(circuloA);       circuloA       = null; }
    if (circuloB)       { map.removeLayer(circuloB);       circuloB       = null; }
    if (lineaConexionA) { map.removeLayer(lineaConexionA); lineaConexionA = null; }
    if (lineaConexionB) { map.removeLayer(lineaConexionB); lineaConexionB = null; }

    // Limpiar panel de itinerario
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
        mostrarItinerario(data);  // ← muestra nombres de rutas y transbordos
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
function dibujarRutaOptima(ruta) {
    if (rutaActual) { map.removeLayer(rutaActual); rutaActual = null; }

    const coordenadas = ruta
        .filter(paso => paso.tipo === "parada")
        .map(paso => [paso.latitud, paso.longitud]);

    if (coordenadas.length === 0) return;

    rutaActual = L.polyline(coordenadas, {
        color: 'blue',
        weight: 6
    }).addTo(map);

    map.fitBounds(rutaActual.getBounds());
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
        radius: 2000,
        color: 'green',
        fillOpacity: 0.07
    }).addTo(map);

    circuloB = L.circle([latB, lonB], {
        radius: 2000,
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

/* ================= ITINERARIO CON NOMBRES DE RUTAS ================= */
function mostrarItinerario(data) {
    const panel = document.getElementById('itinerario');
    if (!panel) return;

    const transbordos = data.ruta_optima.filter(p => p.tipo === 'transbordo');

    let html = `
        <div style="
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
            font-family: sans-serif;
        ">
            <h3 style="margin: 0 0 12px 0; color: #1e293b;">
                🗺️ Itinerario
                <span style="font-size: 13px; font-weight: normal; color: #64748b;">
                    — ${data.total_paradas} paradas · ${transbordos.length} transbordo(s)
                </span>
            </h3>
            <div style="display: flex; flex-direction: column; gap: 8px;">
    `;

    // Origen
    html += `
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:18px;">🟢</span>
            <span><strong>Origen:</strong> ${data.origen.nombre}</span>
        </div>
    `;

    // Rutas y transbordos
    transbordos.forEach((t, i) => {
        html += `
            <div style="
                display: flex;
                align-items: center;
                gap: 8px;
                background: #fef9c3;
                border-left: 4px solid #eab308;
                padding: 8px 12px;
                border-radius: 4px;
            ">
                <span style="font-size:16px;">🚌</span>
                <span>
                    ${i === 0 ? '<strong>Tomar ruta:</strong>' : '<strong>Transbordo → tomar ruta:</strong>'}
                    <strong style="color:#92400e;"> ${t.ruta}</strong>
                </span>
            </div>
        `;
    });

    // Destino
    html += `
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:18px;">🔴</span>
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
        btn.style.cssText = 'background-color:#e1f5fe; cursor:pointer;';
        btn.addEventListener('click', () => mostrarRuta(ruta.coordenadas));

        tdAccion.appendChild(btn);
        tr.appendChild(tdId);
        tr.appendChild(tdNombre);
        tr.appendChild(tdAccion);
        tbody.appendChild(tr);
    });
}

function mostrarRuta(coordenadas) {
    if (rutaActual) { map.removeLayer(rutaActual); rutaActual = null; }
    if (!coordenadas || coordenadas.length === 0) return;

    rutaActual = L.polyline(coordenadas, { color: 'blue', weight: 5 }).addTo(map);
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