/* ================================================================
   simulacion.js  —  Rutas TJ
   Animación de recorrido sobre la ruta calculada por calcularRuta()
   Coloca este archivo en:  static/rutas/js/simulacion.js

   En Mapa.html añade en <head>:
       <link rel="stylesheet" href="{% static 'rutas/css/simulacion.css' %}">
   Y al final del <body> (después de mapa.js):
       <script src="{% static 'rutas/js/simulacion.js' %}"></script>
   ================================================================ */

/* ── Estado de la simulación ── */
const sim = {
    activa:    false,
    pausada:   false,
    pasos:     [],       // array de {lat, lng, nombre?, tipo}
    indice:    0,
    marcador:  null,
    linea:     null,
    trail:     [],       // segmentos del rastro
    intervalo: null,
    velocidad: 400,      // ms entre cada paso (fijo)
};

/* ── Panel de control (se inyecta en el DOM) ── */
function crearPanelSimulacion() {
    if (document.getElementById('sim-panel')) return;

    const panel = document.createElement('div');
    panel.id = 'sim-panel';
    panel.innerHTML = `
        <div class="sim-header">
            <span class="sim-title">
                <span class="sim-bus-icon">🚌</span>
                Simulación de Ruta
            </span>
            <span id="sim-estado" class="sim-badge sim-badge-idle">En espera</span>
        </div>

        <div class="sim-progress-wrap">
            <div class="sim-progress-bar" id="sim-progress-bar"></div>
        </div>
        <div class="sim-progress-labels">
            <span id="sim-step-label">—</span>
            <span id="sim-pct-label">0%</span>
        </div>

        <div class="sim-info-row">
            <div class="sim-info-box">
                <span class="sim-info-icon">📍</span>
                <span class="sim-info-val" id="sim-parada-actual">—</span>
                <span class="sim-info-lbl">parada actual</span>
            </div>
            <div class="sim-info-box">
                <span class="sim-info-icon">🏁</span>
                <span class="sim-info-val" id="sim-total-paradas">—</span>
                <span class="sim-info-lbl">total paradas</span>
            </div>
        </div>

        <div class="sim-btn-row">
            <button id="sim-btn-play"   class="sim-btn sim-btn-primary" onclick="simIniciar()">▶ Iniciar</button>
            <button id="sim-btn-pause"  class="sim-btn sim-btn-secondary" onclick="simPausar()" disabled>⏸ Pausar</button>
            <button id="sim-btn-stop"   class="sim-btn sim-btn-danger"   onclick="simDetener()" disabled>⏹ Detener</button>
        </div>
    `;

    // Insertar después del div#itinerario
    const ref = document.getElementById('itinerario');
    if (ref && ref.parentNode) {
        ref.parentNode.insertBefore(panel, ref.nextSibling);
    } else {
        document.querySelector('main').appendChild(panel);
    }

}

/* ── Icono del marcador animado ── */
function iconoMovil(done = false) {
    return L.divIcon({
        className: '',
        html: `<div class="sim-marker-icon${done ? ' sim-marker-done' : ''}">🚌</div>`,
        iconSize:   [28, 28],
        iconAnchor: [14, 14],
    });
}

/* ── Cargar pasos desde la última ruta calculada ── */
function cargarPasosDesdeRuta(rutaOptima) {
    // Solo "parada" tiene latitud/longitud — los transbordos no tienen coordenadas
    sim.pasos = rutaOptima
        .filter(p => p.tipo === 'parada' && p.latitud != null && p.longitud != null)
        .map(p => ({
            lat:    p.latitud,
            lng:    p.longitud,
            nombre: p.nombre || '—',
            tipo:   p.tipo,
        }));
}

/* ── Actualizar UI del panel ── */
function simActualizarUI() {
    const total = sim.pasos.length;
    const i     = sim.indice;
    const pct   = total > 1 ? Math.round((i / (total - 1)) * 100) : 0;

    document.getElementById('sim-progress-bar').style.width = pct + '%';
    document.getElementById('sim-pct-label').textContent    = pct + '%';
    document.getElementById('sim-step-label').textContent   = `Paso ${i + 1} / ${total}`;
    document.getElementById('sim-total-paradas').textContent = total;

    const paso = sim.pasos[i];
    if (paso) {
        document.getElementById('sim-parada-actual').textContent = paso.nombre;
    }
}

/* ── Mover el marcador al paso actual ── */
function simMoverPaso() {
    if (sim.indice >= sim.pasos.length) {
        simFinalizar();
        return;
    }

    const paso = sim.pasos[sim.indice];

    // Crear marcador si no existe
    if (!sim.marcador) {
        sim.marcador = L.marker([paso.lat, paso.lng], { icon: iconoMovil() }).addTo(map);
    } else {
        sim.marcador.setLatLng([paso.lat, paso.lng]);
    }

    // Rastro: agregar segmento
    if (sim.indice > 0) {
        const prev = sim.pasos[sim.indice - 1];
        const seg  = L.polyline(
            [[prev.lat, prev.lng], [paso.lat, paso.lng]],
            { color: '#0d9488', weight: 5, opacity: 0.85 }
        ).addTo(map);
        sim.trail.push(seg);
    }

    // Centrar mapa suavemente
    map.panTo([paso.lat, paso.lng], { animate: true, duration: 0.5 });

    simActualizarUI();
    sim.indice++;
}

/* ── Finalizar simulación ── */
function simFinalizar() {
    clearInterval(sim.intervalo);
    sim.activa  = false;
    sim.pausada = false;

    if (sim.marcador) sim.marcador.setIcon(iconoMovil(true));

    document.getElementById('sim-estado').textContent  = 'Completado';
    document.getElementById('sim-estado').className    = 'sim-badge sim-badge-done';
    document.getElementById('sim-btn-play').disabled   = false;
    document.getElementById('sim-btn-play').textContent = '↺ Reiniciar';
    document.getElementById('sim-btn-pause').disabled  = true;
    document.getElementById('sim-btn-stop').disabled   = true;
}

/* ── Limpiar capas de simulación del mapa ── */
function simLimpiarCapas() {
    if (sim.marcador) { map.removeLayer(sim.marcador); sim.marcador = null; }
    sim.trail.forEach(seg => map.removeLayer(seg));
    sim.trail = [];
}

/* ── API pública ── */

function simIniciar() {
    // Si no hay pasos, la ruta aún no se calculó
    if (sim.pasos.length === 0) {
        alert('Primero calcula una ruta para poder simularla.');
        return;
    }

    // Reiniciar si ya terminó
    simLimpiarCapas();
    sim.indice  = 0;
    sim.activa  = true;
    sim.pausada = false;

    document.getElementById('sim-estado').textContent = 'En curso';
    document.getElementById('sim-estado').className   = 'sim-badge sim-badge-running';
    document.getElementById('sim-btn-play').disabled  = true;
    document.getElementById('sim-btn-pause').disabled = false;
    document.getElementById('sim-btn-stop').disabled  = false;

    sim.intervalo = setInterval(simMoverPaso, sim.velocidad);
}

function simPausar() {
    if (!sim.activa) return;

    if (!sim.pausada) {
        clearInterval(sim.intervalo);
        sim.pausada = true;
        document.getElementById('sim-btn-pause').textContent = '▶ Reanudar';
        document.getElementById('sim-estado').textContent    = 'Pausado';
        document.getElementById('sim-estado').className      = 'sim-badge sim-badge-paused';
    } else {
        sim.intervalo = setInterval(simMoverPaso, sim.velocidad);
        sim.pausada   = false;
        document.getElementById('sim-btn-pause').textContent = '⏸ Pausar';
        document.getElementById('sim-estado').textContent    = 'En curso';
        document.getElementById('sim-estado').className      = 'sim-badge sim-badge-running';
    }
}

function simDetener() {
    clearInterval(sim.intervalo);
    simLimpiarCapas();
    sim.activa  = false;
    sim.pausada = false;
    sim.indice  = 0;

    document.getElementById('sim-estado').textContent  = 'En espera';
    document.getElementById('sim-estado').className    = 'sim-badge sim-badge-idle';
    document.getElementById('sim-btn-play').disabled   = false;
    document.getElementById('sim-btn-play').textContent = '▶ Iniciar';
    document.getElementById('sim-btn-pause').disabled  = true;
    document.getElementById('sim-btn-pause').textContent = '⏸ Pausar';
    document.getElementById('sim-btn-stop').disabled   = true;

    document.getElementById('sim-progress-bar').style.width = '0%';
    document.getElementById('sim-pct-label').textContent    = '0%';
    document.getElementById('sim-step-label').textContent   = '—';
    document.getElementById('sim-parada-actual').textContent = '—';
}

/* ================================================================
   INTEGRACIÓN CON mapa.js
   Interceptamos dibujarRutaOptima para cargar los pasos
   automáticamente cada vez que se calcula una ruta.
   ================================================================ */
(function parchearDibujarRuta() {
    const original = window.dibujarRutaOptima;
    window.dibujarRutaOptima = function (ruta) {
        original(ruta);              // comportamiento original intacto
        cargarPasosDesdeRuta(ruta);  // cargamos pasos para la simulación
        simDetener();                // reiniciamos el panel
    };
})();

/* ── Inicialización ── */
document.addEventListener('DOMContentLoaded', function () {
    crearPanelSimulacion();
});

/* ── Parche limpiarMapa ── */
(function parchearLimpiarMapa() {
    const original = window.limpiarMapa;
    window.limpiarMapa = function () {
        original();         // limpia marcadores, ruta, círculos, etc.
        simDetener();       // detiene la simulación y resetea el panel
        simLimpiarCapas();  // elimina el camión y el rastro verde del mapa
        sim.pasos = [];     // borra los pasos para que no se pueda reiniciar
    };
})();