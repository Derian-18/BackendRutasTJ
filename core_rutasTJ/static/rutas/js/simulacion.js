/* ================================================================
   simulacion.js  —  Rutas TJ
   Animación de recorrido sobre la ruta calculada por calcularRuta()
   Coloca este archivo en:  static/rutas/js/simulacion.js
   Añade en Mapa.html (después de mapa.js):
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
    velocidad: 700,      // ms entre cada paso
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

        <div class="sim-speed-row">
            <label for="sim-speed">Velocidad</label>
            <input type="range" id="sim-speed" min="200" max="2000" step="100" value="700">
            <span id="sim-speed-label">Normal</span>
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

    // Listener de velocidad
    document.getElementById('sim-speed').addEventListener('input', function () {
        const v = parseInt(this.value);
        sim.velocidad = v;
        if      (v <= 400)  document.getElementById('sim-speed-label').textContent = '🐇 Rápido';
        else if (v <= 900)  document.getElementById('sim-speed-label').textContent = 'Normal';
        else                document.getElementById('sim-speed-label').textContent = '🐢 Lento';
    });
}

/* ── Inyectar estilos del panel ── */
function inyectarEstilos() {
    if (document.getElementById('sim-styles')) return;
    const style = document.createElement('style');
    style.id = 'sim-styles';
    style.textContent = `
        #sim-panel {
            background: #0f172a;
            border: 1px solid #1e3a5f;
            border-radius: 12px;
            padding: 18px 20px;
            margin: 18px 0;
            color: #e2e8f0;
            font-family: 'Segoe UI', system-ui, sans-serif;
            box-shadow: 0 4px 24px rgba(0,0,0,0.35);
        }
        .sim-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
        }
        .sim-title {
            font-size: 1rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            color: #f1f5f9;
        }
        .sim-bus-icon { margin-right: 6px; }
        .sim-badge {
            font-size: 0.72rem;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 20px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .sim-badge-idle    { background: #1e293b; color: #64748b; }
        .sim-badge-running { background: #0d9488; color: #fff; animation: simPulse 1.4s infinite; }
        .sim-badge-paused  { background: #b45309; color: #fff; }
        .sim-badge-done    { background: #166534; color: #bbf7d0; }

        @keyframes simPulse {
            0%, 100% { opacity: 1; }
            50%       { opacity: 0.55; }
        }

        .sim-progress-wrap {
            background: #1e293b;
            border-radius: 6px;
            height: 8px;
            overflow: hidden;
            margin-bottom: 4px;
        }
        .sim-progress-bar {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #0d9488, #38bdf8);
            border-radius: 6px;
            transition: width 0.5s ease;
        }
        .sim-progress-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #64748b;
            margin-bottom: 14px;
        }

        .sim-info-row {
            display: flex;
            gap: 12px;
            margin-bottom: 14px;
        }
        .sim-info-box {
            flex: 1;
            background: #1e293b;
            border-radius: 8px;
            padding: 10px 12px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .sim-info-icon { font-size: 1rem; }
        .sim-info-val  { font-size: 1.1rem; font-weight: 700; color: #38bdf8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .sim-info-lbl  { font-size: 0.68rem; color: #475569; text-transform: uppercase; letter-spacing: 0.06em; }

        .sim-speed-row {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.8rem;
            color: #94a3b8;
            margin-bottom: 14px;
        }
        #sim-speed {
            flex: 1;
            accent-color: #0d9488;
            cursor: pointer;
        }
        #sim-speed-label { min-width: 60px; color: #cbd5e1; font-weight: 600; }

        .sim-btn-row {
            display: flex;
            gap: 8px;
        }
        .sim-btn {
            flex: 1;
            padding: 9px 0;
            border: none;
            border-radius: 7px;
            font-size: 0.82rem;
            font-weight: 700;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
            letter-spacing: 0.02em;
        }
        .sim-btn:disabled { opacity: 0.3; cursor: not-allowed; }
        .sim-btn:not(:disabled):hover { opacity: 0.88; transform: translateY(-1px); }
        .sim-btn-primary   { background: #0d9488; color: #fff; }
        .sim-btn-secondary { background: #334155; color: #e2e8f0; }
        .sim-btn-danger    { background: #7f1d1d; color: #fca5a5; }

        /* Marcador animado */
        @keyframes simBounce {
            0%, 100% { transform: translateY(0) scale(1); }
            50%       { transform: translateY(-6px) scale(1.1); }
        }
        .sim-marker-icon {
            font-size: 22px;
            animation: simBounce 0.9s ease-in-out infinite;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.6));
        }
        .sim-marker-icon.sim-marker-done {
            animation: none;
            font-size: 26px;
        }
    `;
    document.head.appendChild(style);
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
    inyectarEstilos();
    crearPanelSimulacion();
});