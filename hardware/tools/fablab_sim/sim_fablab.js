// Corre los .nc de la tarjeta Cubiko en el simulador del Fab Lab (https://fablab.sebs.mx/cnc/):
// homing, material, cero XY, Z con sonda, mapa de alturas y cada trabajo con el boton "Mill" de la app.
// Requiere Playwright y acceso a fablab.sebs.mx. Ver hardware/cubiko/README.md.
// Uso: node sim_full.js <lado: 1|2> <prefijo> <velocidad> archivos...
// Lado 1: .nc del lado 1. Lado 2: Gerbers (F_Cu, Edge_Cuts, .drl) + .nc del lado 2, con alineacion por 2 barrenos.
const { chromium } = require('playwright');
const [,, lado, pref, vel, ...files] = process.argv;
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage({ viewport: { width: 1500, height: 950 } });
  p.setDefaultTimeout(0);
  p.on('pageerror', e => console.log('PAGEERROR ' + e.message));
  const t0 = Date.now(); const T = () => ((Date.now() - t0) / 1000).toFixed(0) + 's';
  const step = async (name, fn, arg) => { const r = await p.evaluate(fn, arg); console.log(`[${T()}] ${name}: ${JSON.stringify(r)}`); return r; };
  await p.goto('https://fablab.sebs.mx/cnc/', { waitUntil: 'load', timeout: 90000 });
  await p.waitForFunction(() => window.__cnc && window.__cnc.app);
  await step('simulacion + homing', async () => {
    const { app, grbl } = window.__cnc;
    await app.acc.cambiarModo('sim'); await app.acc.conectar('sim'); await new Promise(r => setTimeout(r, 800));
    grbl.sim.velocidad = 50; await app.acc.homing();
    return { estado: grbl.est.estado, mpos: grbl.est.mpos };
  });
  await step('material FR1 142x100x1.6 (diseno a X3 Y2)', async () => {
    const { app, S } = window.__cnc;
    for (const [k, v] of [['ancho', 142], ['alto', 100], ['grosor', 1.6], ['x', 3], ['y', 2]]) await app.acc.ponerMaterial(k, v);
    return S.material;
  });
  await step('cero XY en la esquina del blank (el MISMO en las 2 caras)', async () => {
    const { app, grbl } = window.__cnc;
    await grbl.enviarVarias(['G90', 'G53 G0 Z-2', 'G53 G0 X-142 Y-107']); await grbl.esperarQuieto();
    await app.acc.fijarXY();
    return { mpos: grbl.est.mpos };
  });
  await p.setInputFiles('#archivos', files);
  await p.waitForFunction((n) => window.__cnc.S.trabajos.filter(t => t.origen === 'nc').length >= n, files.filter(f => f.endsWith('.nc')).length);
  await step('archivos', async () => { const { S } = window.__cnc; return { trabajos: S.trabajos.filter(t => t.origen === 'nc').map(t => `${t.nombre} [${t.herramienta}] ${t.lineas.length} lineas`), gerber: S.pcb ? { nombre: S.pcb.nombre, hoyos: S.pcb.hoyos.length } : null }; });
  if (lado === '2') {
    await step('alineacion con 2 barrenos (H1 y barreno sup. der. de la Pi)', async () => {
      const { grbl, S } = window.__cnc;
      const { alineacion } = await import('/shared-en/js/gcode.js');
      // posiciones de diseno (lado 2, cara superior arriba): X = 3 + x, Y = 2 + (96 - y)
      const A = { x: 3 + 3.5, y: 2 + 96 - 8.5 }, B = { x: 3 + 132.5, y: 2 + 96 - 8.5 };
      const med = {};
      for (const [k, h] of [['A', A], ['B', B]]) {
        await grbl.enviarVarias(['G90', 'G53 G0 Z-2', `G0 X${h.x} Y${h.y}`]); await grbl.esperarQuieto();
        med[k] = { ...grbl.est.wpos };      // en la maquina: la fresa centrada en el barreno
      }
      const al = alineacion(A, B, med.A, med.B);
      S.alinear = al;
      return { A, B, medidoA: med.A, medidoB: med.B, rotacion_grados: +(al.ang * 180 / Math.PI).toFixed(4), dx: +al.dx.toFixed(3), dy: +al.dy.toFixed(3) };
    });
  }
  await step('Z0 con la sonda', async () => {
    const { grbl, S } = window.__cnc;
    grbl.sim.velocidad = 50; if (grbl.est.estado === 'Alarm') await grbl.enviar('$X');
    await grbl.enviarVarias(['G90', 'G53 G0 Z-2', 'G0 X5 Y5']); await grbl.esperarQuieto();
    await grbl.enviarVarias(['G21', 'G91']);
    let r = await grbl.sondear('G38.2 Z-38 F300');
    if (r) { await grbl.enviar('G0 Z1'); r = await grbl.sondear('G38.2 Z-2 F20'); }
    await grbl.enviar('G10 L20 P1 Z0'); await grbl.enviarVarias(['G0 Z5', 'G90']); await grbl.esperarQuieto();
    S.zListo = true; S.alarma = null;
    if (!r) return { error: 'la sonda no toco', estado: grbl.est.estado };
    return { z_maquina: r.z, wco_z: grbl.est.wco.z };
  });
  await step('mapa de alturas 11x8 sobre la tarjeta', async () => {
    const { grbl, S, visor } = window.__cnc;
    const { MapaAlturas } = await import('/cnc/js/alturas.js');
    const m = new MapaAlturas({ x: 3, y: 2, ancho: 136, alto: 96, nx: 11, ny: 8 });
    grbl.sim.velocidad = 200;
    await grbl.enviarVarias(['G21', 'G90', 'G0 Z2']);
    for (const q of m.recorrido()) {
      await grbl.enviar(`G0 X${q.x.toFixed(3)} Y${q.y.toFixed(3)}`);
      const r = await grbl.sondear('G38.2 Z-3 F150');
      if (!r) return { falla: q };
      m.valores[q.j][q.i] = r.z - grbl.est.wco.z;
      await grbl.enviar('G0 Z2');
    }
    await grbl.enviar('G0 Z5');
    S.mapa = m; S.usarMapa = true; S.sinMapa = false; visor.ponerMalla(null);
    return { puntos: 88, min: +m.rango.min.toFixed(3), max: +m.rango.max.toFixed(3) };
  });
  const ids = await p.evaluate(() => window.__cnc.S.trabajos.filter(t => t.origen === 'nc').sort((a, b) => a.nombre.localeCompare(b.nombre)).map(t => t.id));
  for (const id of ids) {
    await p.evaluate((v) => { window.__cnc.grbl.sim.velocidad = +v; window.__cnc.S.herramientaZ = null; }, vel);
    // el gemelo 3D se dibuja por software (sin GPU): se pausa el dibujo durante el trabajo
    await p.evaluate(() => window.__cnc.visor.renderer.setAnimationLoop(null));
    const nombre = await p.evaluate((id) => window.__cnc.S.trabajos.find(t => t.id === id).nombre, id);
    const tj = Date.now();
    const run = p.evaluate((id) => { const { app, S } = window.__cnc; return app.acc.correrTrabajo(S.trabajos.find(t => t.id === id), { aire: false }); }, id);
    for (let k = 0; k < 60; k++) {
      await p.waitForTimeout(500);
      const d = await p.evaluate(async () => {
        const dl = [...document.querySelectorAll('dialog[open], [role=dialog], [role=alertdialog], .hoja')].filter(x => (x.offsetParent || x.open) && /\bMill\b/.test(x.innerText));
        if (!dl.length) return { ok: false, txt: [] };
        const x = dl[dl.length - 1];
        x.querySelectorAll('input[type=checkbox]').forEach(c => { if (!c.checked) c.click(); });
        await new Promise(r => setTimeout(r, 300));
        const btn = [...x.querySelectorAll('button')].find(b => b.innerText.trim() === 'Mill' && !b.disabled);
        const txt = x.innerText.replace(/\s+/g, ' ').slice(0, 300);
        if (btn) { btn.click(); return { ok: true, txt: [txt] }; }
        return { ok: false, txt: [txt] };
      });
      if (d.ok) { await p.waitForTimeout(1500); if (await p.evaluate(() => !!window.__cnc.S.prog)) { console.log(`[${T()}]   app: ${d.txt.join(' | ')}`); break; } }
      if (k === 59) console.log('   SIN BOTON (la app pide otra cosa):', d.txt.join(' | '));
    }
    const iniciado = await p.evaluate(() => !!window.__cnc.S.prog);
    if (!iniciado) { const t = await p.evaluate(() => [...document.querySelectorAll('dialog[open], [role=dialog], [role=alertdialog], .hoja')].map(x => x.innerText.replace(/\s+/g, ' ').slice(0, 400))); console.log('   NO ARRANCO:', t.join(' | ')); }
    const iv = setInterval(async () => {
      try { const s = await p.evaluate(() => { const { S, grbl } = window.__cnc; return S.prog ? `${S.prog.h}/${S.prog.n} lineas · ${grbl.est.estado} · W ${grbl.est.wpos.x.toFixed(1)},${grbl.est.wpos.y.toFixed(1)},${grbl.est.wpos.z.toFixed(2)}` : 'sin progreso'; }); console.log(`[${T()}]     ${nombre}: ${s}`); } catch (e) {}
    }, 20000);
    await run;
    clearInterval(iv);
    const st = await p.evaluate((id) => { const { S, grbl } = window.__cnc; return { estado: S.trabajos.find(t => t.id === id).estado, grbl: grbl.est.estado }; }, id);
    console.log(`[${T()}] TRABAJO ${nombre}: ${JSON.stringify(st)} en ${((Date.now() - tj) / 1000).toFixed(0)} s reales`);
    await p.evaluate(() => { const v = window.__cnc.visor; v.renderer.setAnimationLoop((t) => { v._cuadro(t); v.controls.update(); v.renderer.render(v.scene, v.camera); }); });
    await p.click('#vistas button[data-vista="arriba"]').catch(() => {});
    await p.waitForTimeout(2500);
    await p.screenshot({ path: `${pref}_${nombre}.png` });
  }
  await p.click('#vistas button[data-vista="3d"]').catch(() => {});
  await p.waitForTimeout(1500);
  await p.screenshot({ path: `${pref}_3d.png` });
  const cons = await p.evaluate(() => { const c = document.querySelector('#consola, .consola'); return c ? c.innerText.split('\n').slice(-30).join('\n') : ''; });
  console.log('--- consola de la app:\n' + cons);
  console.log('FIN');
  await b.close();
})();
