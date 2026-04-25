/* ================================================================
   simulacion.js  —  Lógica pura de simulación
   Responsabilidad: estado de la simulación, movimiento del marcador
   en el mapa y ciclo de vida (iniciar / pausar / detener / finalizar).
   NO toca el DOM directamente — delega en simulacion-ui.js mediante
   las funciones simUI.*
   ================================================================ */

/* ── Estado ── */
const sim = {
    activa:    false,
    pausada:   false,
    pasos:     [],
    indice:    0,
    marcador:  null,
    trail:     [],
    intervalo: null,
    velocidad: 400,   // ms entre cada paso
};

/* ── Icono del marcador animado ── */
function iconoMovil(done = false) {
    return L.divIcon({
        className: '',
        html: `<div class="sim-marker-icon${done ? ' sim-marker-done' : ''}">🚌</div>`,
        iconSize:   [28, 28],
        iconAnchor: [14, 14],
    });
}

/* ── Cargar pasos desde la ruta calculada ── */
function cargarPasosDesdeRuta(rutaOptima) {
    sim.pasos = rutaOptima
        .filter(p => p.tipo === 'parada' && p.latitud != null && p.longitud != null)
        .map(p => ({
            lat:    p.latitud,
            lng:    p.longitud,
            nombre: p.nombre || '—',
        }));
}

/* ── Mover el marcador al paso actual ── */
function simMoverPaso() {
    if (sim.indice >= sim.pasos.length) {
        simFinalizar();
        return;
    }

    const paso = sim.pasos[sim.indice];

    if (!sim.marcador) {
        sim.marcador = L.marker([paso.lat, paso.lng], { icon: iconoMovil() }).addTo(map);
    } else {
        sim.marcador.setLatLng([paso.lat, paso.lng]);
    }

    if (sim.indice > 0) {
        const prev = sim.pasos[sim.indice - 1];
        const seg  = L.polyline(
            [[prev.lat, prev.lng], [paso.lat, paso.lng]],
            { color: '#0d9488', weight: 5, opacity: 0.85 }
        ).addTo(map);
        sim.trail.push(seg);
    }

    map.panTo([paso.lat, paso.lng], { animate: true, duration: 0.5 });

    simUI.actualizarPaso(sim.indice, sim.pasos.length, paso.nombre);
    sim.indice++;
}

/* ── Limpiar capas del mapa ── */
function simLimpiarCapas() {
    if (sim.marcador) { map.removeLayer(sim.marcador); sim.marcador = null; }
    sim.trail.forEach(seg => map.removeLayer(seg));
    sim.trail = [];
}

/* ── Finalizar ── */
function simFinalizar() {
    clearInterval(sim.intervalo);
    sim.activa  = false;
    sim.pausada = false;

    if (sim.marcador) sim.marcador.setIcon(iconoMovil(true));

    simUI.estadoCompletado();
}

/* ── API pública ── */

function simIniciar() {
    if (sim.pasos.length === 0) {
        alert('Primero calcula una ruta para poder simularla.');
        return;
    }

    simLimpiarCapas();
    sim.indice  = 0;
    sim.activa  = true;
    sim.pausada = false;

    simUI.estadoEnCurso();
    sim.intervalo = setInterval(simMoverPaso, sim.velocidad);
}

function simPausar() {
    if (!sim.activa) return;

    if (!sim.pausada) {
        clearInterval(sim.intervalo);
        sim.pausada = true;
        simUI.estadoPausado();
    } else {
        sim.intervalo = setInterval(simMoverPaso, sim.velocidad);
        sim.pausada   = false;
        simUI.estadoEnCurso();
    }
}

function simDetener() {
    clearInterval(sim.intervalo);
    simLimpiarCapas();
    sim.activa  = false;
    sim.pausada = false;
    sim.indice  = 0;

    simUI.estadoEnEspera();
}

/* ── Integración con mapa.js ── */

(function parchearDibujarRuta() {
    const original = window.dibujarRutaOptima;
    window.dibujarRutaOptima = function (ruta) {
        original(ruta);
        cargarPasosDesdeRuta(ruta);
        simDetener();
    };
})();

(function parchearLimpiarMapa() {
    const original = window.limpiarMapa;
    window.limpiarMapa = function () {
        original();
        simDetener();
        simLimpiarCapas();
        sim.pasos = [];
    };
})();