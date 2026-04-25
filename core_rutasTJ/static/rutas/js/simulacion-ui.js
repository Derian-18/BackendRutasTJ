/* ================================================================
   simulacion-ui.js  —  Capa de presentación del panel de simulación
   Responsabilidad: leer y escribir el DOM del #sim-panel.
   NO contiene lógica de simulación ni referencias al mapa.
   Es llamado exclusivamente desde simulacion.js mediante simUI.*
   ================================================================ */

const simUI = (() => {

    /* ── Referencias a elementos del DOM ── */
    const el = {
        estado:       () => document.getElementById('sim-estado'),
        progressBar:  () => document.getElementById('sim-progress-bar'),
        pctLabel:     () => document.getElementById('sim-pct-label'),
        stepLabel:    () => document.getElementById('sim-step-label'),

        btnPlay:      () => document.getElementById('sim-btn-play'),
        btnPause:     () => document.getElementById('sim-btn-pause'),
        btnStop:      () => document.getElementById('sim-btn-stop'),
    };

    /* ── Helpers internos ── */
    function setBadge(texto, clase) {
        const e = el.estado();
        e.textContent = texto;
        e.className   = `sim-badge ${clase}`;
    }

    function setBotones({ playDisabled, playTexto, pauseDisabled, pauseTexto, stopDisabled }) {
        const play  = el.btnPlay();
        const pause = el.btnPause();
        const stop  = el.btnStop();

        play.disabled   = playDisabled;
        play.textContent = playTexto;
        pause.disabled  = pauseDisabled;
        pause.textContent = pauseTexto;
        stop.disabled   = stopDisabled;
    }

    function resetProgreso() {
        el.progressBar().style.width    = '0%';
        el.pctLabel().textContent       = '0%';
        el.stepLabel().textContent      = '—';

    }

    /* ── API pública ── */
    return {

        /* Llamado en cada paso de la simulación */
        actualizarPaso(indice, total, nombreParada) {
            const pct = total > 1 ? Math.round((indice / (total - 1)) * 100) : 0;

            el.progressBar().style.width      = pct + '%';
            el.pctLabel().textContent         = pct + '%';
            el.stepLabel().textContent        = `Paso ${indice + 1} / ${total}`;

        },

        estadoEnCurso() {
            setBadge('En curso', 'sim-badge-running');
            setBotones({
                playDisabled:  true,
                playTexto:     '▶ Iniciar',
                pauseDisabled: false,
                pauseTexto:    '⏸ Pausar',
                stopDisabled:  false,
            });
        },

        estadoPausado() {
            setBadge('Pausado', 'sim-badge-paused');
            setBotones({
                playDisabled:  true,
                playTexto:     '▶ Iniciar',
                pauseDisabled: false,
                pauseTexto:    '▶ Reanudar',
                stopDisabled:  false,
            });
        },

        estadoCompletado() {
            setBadge('Completado', 'sim-badge-done');
            setBotones({
                playDisabled:  false,
                playTexto:     '↺ Reiniciar',
                pauseDisabled: true,
                pauseTexto:    '⏸ Pausar',
                stopDisabled:  true,
            });
        },

        estadoEnEspera() {
            setBadge('En espera', 'sim-badge-idle');
            setBotones({
                playDisabled:  false,
                playTexto:     '▶ Iniciar',
                pauseDisabled: true,
                pauseTexto:    '⏸ Pausar',
                stopDisabled:  true,
            });
            resetProgreso();
        },
    };
})();