/* CUT 08: visibly travelling gold arrow, revealed metallic ribbon and bar light.
 * Draw over assets/cut08-clean.png, before the Korean DOM typography.
 * All motion is a pure function of explicit local seconds; no clock or randomness.
 * Coordinates assume the 1920 x 1080 stage and a stable CUT 08 camera.
 * These unlabelled bars are conceptual reference imagery, not measured results.
 */
(function installHeroEffect(global) {
  'use strict';
  const WIDTH = 1920, HEIGHT = 1080, COPY_BOUNDARY = 1235;
  const PATH = [[-70, 855], [440, 775], [795, 580], [1020, 116]];
  const clamp01 = value => Math.max(0, Math.min(1, value));
  const smooth = value => { const q = clamp01(value); return q * q * (3 - 2 * q); };
  const seeded = value => { const n = Math.sin(value * 127.1 + 311.7) * 43758.5453; return n - Math.floor(n); };
  function point(q) {
    const a = 1 - q;
    return { x: a ** 3 * PATH[0][0] + 3 * a * a * q * PATH[1][0] + 3 * a * q * q * PATH[2][0] + q ** 3 * PATH[3][0],
      y: a ** 3 * PATH[0][1] + 3 * a * a * q * PATH[1][1] + 3 * a * q * q * PATH[2][1] + q ** 3 * PATH[3][1] };
  }
  function direction(q) {
    const a = 1 - q;
    const dx = 3 * a * a * (PATH[1][0] - PATH[0][0]) + 6 * a * q * (PATH[2][0] - PATH[1][0]) + 3 * q * q * (PATH[3][0] - PATH[2][0]);
    const dy = 3 * a * a * (PATH[1][1] - PATH[0][1]) + 6 * a * q * (PATH[2][1] - PATH[1][1]) + 3 * q * q * (PATH[3][1] - PATH[2][1]);
    const length = Math.hypot(dx, dy);
    return { x: dx / length, y: dy / length, nx: -dy / length, ny: dx / length };
  }
  function state(t, duration) {
    t = Math.max(0, Number(t) || 0);
    const travel = Math.min(3.55, Math.max(2.8, (Number(duration) || 7) * .53));
    const q = clamp01((t - .22) / travel);
    const progress = .5 - .5 * Math.cos(q * Math.PI);
    return { t, progress, tip: point(progress), tangent: direction(progress),
      reveal: smooth(t / .38), travel_seconds: travel, arrived: q >= 1,
      bounds: { left: 0, top: 0, right: COPY_BOUNDARY, bottom: HEIGHT } };
  }
  function trace(ctx, from, to, offset = 0) {
    const steps = Math.max(2, Math.ceil((to - from) * 160));
    ctx.beginPath();
    for (let k = 0; k <= steps; k++) {
      const q = from + (to - from) * k / steps, p = point(q), d = direction(q);
      const x = p.x + d.nx * offset, y = p.y + d.ny * offset;
      if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
  }
  function halo(ctx, x, y, radius, opacity) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, radius);
    g.addColorStop(0, `rgba(255,241,195,${opacity})`);
    g.addColorStop(.16, `rgba(255,206,119,${opacity * .7})`);
    g.addColorStop(.52, `rgba(255,169,52,${opacity * .23})`);
    g.addColorStop(1, 'rgba(255,179,71,0)');
    ctx.fillStyle = g; ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  }
  function polygon(ctx, vertices) {
    ctx.beginPath(); vertices.forEach((p, index) => index ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)); ctx.closePath();
  }
  function ribbon(ctx, s) {
    const alpha = s.reveal;
    // End the ribbon inside the solid arrowhead, keeping rounded stroke caps
    // from appearing as separate circles in front of its sharp leading tip.
    const trailTo = Math.max(0, s.progress - .065);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    trace(ctx, 0, trailTo); ctx.strokeStyle = `rgba(255,159,39,${.11 * alpha})`;
    ctx.lineWidth = 55; ctx.shadowColor = '#FFB347'; ctx.shadowBlur = 42; ctx.stroke();
    trace(ctx, 0, trailTo); ctx.strokeStyle = `rgba(255,202,111,${.26 * alpha})`;
    ctx.lineWidth = 34; ctx.shadowBlur = 20; ctx.stroke(); ctx.restore();
    // Dark bronze under-bevel gives the bright ribbon physical depth.
    ctx.save(); ctx.globalAlpha = alpha;
    trace(ctx, 0, trailTo, 6); ctx.strokeStyle = '#704115'; ctx.lineWidth = 26; ctx.stroke();
    const metal = ctx.createLinearGradient(0, 850, 1050, 110);
    metal.addColorStop(0, '#D39A46'); metal.addColorStop(.3, '#F5D6A6');
    metal.addColorStop(.56, '#F0AD45'); metal.addColorStop(.8, '#FFF0C5'); metal.addColorStop(1, '#FFCF76');
    trace(ctx, 0, trailTo); ctx.strokeStyle = metal; ctx.lineWidth = 23;
    ctx.shadowColor = '#FFB347'; ctx.shadowBlur = 16; ctx.stroke();
    ctx.shadowBlur = 0;
    trace(ctx, 0, trailTo, -5); ctx.strokeStyle = '#FFF8DE'; ctx.lineWidth = 5; ctx.globalAlpha = .91 * alpha; ctx.stroke();
    trace(ctx, 0, trailTo, 5); ctx.strokeStyle = '#AC6C1F'; ctx.lineWidth = 2.5; ctx.globalAlpha = .72 * alpha; ctx.stroke();
    ctx.restore();
    // Thin luminous companion strands move with the newly drawn ribbon.
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    for (const offset of [-30, 27]) {
      trace(ctx, 0, Math.max(0, s.progress - .09), offset);
      ctx.strokeStyle = `rgba(255,203,125,${.55 * alpha})`; ctx.lineWidth = 1.6;
      ctx.shadowColor = '#FFB347'; ctx.shadowBlur = 11; ctx.stroke();
    }
    // Energy packets continue climbing after the arrow reaches the summit.
    for (let k = 0; k < 4; k++) {
      const q = (s.t * .26 + k * .25) % 1;
      if (q > trailTo || q < .015) continue;
      trace(ctx, Math.max(0, q - .055), q, k % 2 ? 28 : -29);
      ctx.strokeStyle = `rgba(255,249,220,${.82 * alpha})`; ctx.lineWidth = 2.7; ctx.shadowBlur = 17; ctx.stroke();
    }
    ctx.restore();
  }
  function sparks(ctx, s) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    for (let k = 0; k < 78; k++) {
      const q = (seeded(k + 41) + s.t * (.095 + seeded(k + 83) * .018)) % 1;
      if (q >= s.progress || q < .015) continue;
      const p = point(q), d = direction(q), side = (seeded(k + 15) * 2 - 1) * (23 + seeded(k + 62) * 36);
      const radius = .9 + seeded(k + 98) * 2.1;
      const strength = (.25 + seeded(k + 5) * .56) * s.reveal;
      const x = p.x + d.nx * side, y = p.y + d.ny * side;
      ctx.shadowColor = '#FFBD5E'; ctx.shadowBlur = 8; ctx.fillStyle = `rgba(255,222,166,${strength})`;
      ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }
  function arrowhead(ctx, s) {
    const d = s.tangent, tip = s.tip, scale = .82 + .18 * smooth(s.t / .9);
    const vertex = (along, sideways, dx = 0, dy = 0) => ({
      x: tip.x + d.x * along * scale + d.nx * sideways * scale + dx,
      y: tip.y + d.y * along * scale + d.ny * sideways * scale + dy });
    const vertices = [vertex(0, 0), vertex(-117, -67), vertex(-91, -23),
      vertex(-139, -23), vertex(-139, 23), vertex(-91, 23), vertex(-117, 67)];
    ctx.save(); ctx.globalAlpha = s.reveal;
    // Offset side face and warm metallic main face form an actual 3D arrowhead.
    polygon(ctx, vertices.map(p => ({ x: p.x + 6, y: p.y + 8 })));
    ctx.fillStyle = '#A56216'; ctx.shadowColor = '#FFB347'; ctx.shadowBlur = 25; ctx.fill();
    const face = ctx.createLinearGradient(tip.x - d.nx * 70, tip.y - d.ny * 70, tip.x + d.nx * 70, tip.y + d.ny * 70);
    face.addColorStop(0, '#BF781F'); face.addColorStop(.2, '#F2BB67');
    face.addColorStop(.47, '#FFF6D6'); face.addColorStop(.62, '#FFE3A1'); face.addColorStop(1, '#DB982F');
    polygon(ctx, vertices); ctx.fillStyle = face; ctx.fill();
    ctx.shadowBlur = 0; ctx.lineWidth = 2.2; ctx.strokeStyle = '#FFF0C5'; ctx.stroke();
    const ridge = [vertex(0, 0), vertex(-117, -67), vertex(-91, -23), vertex(-139, -23)];
    ctx.beginPath(); ridge.forEach((p, index) => index ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
    ctx.strokeStyle = '#FFFBE5'; ctx.lineWidth = 3.1; ctx.stroke();
    ctx.globalCompositeOperation = 'screen';
    halo(ctx, tip.x - d.x * 30, tip.y - d.y * 30, 94, (.21 + .035 * Math.sin(s.t * 2.3)) * s.reveal);
    halo(ctx, tip.x - d.x * 18, tip.y - d.y * 18, 46, .20 * s.reveal);
    ctx.restore();
  }
  // Photographic bars remain unchanged. Their existing top/face edges receive
  // sequential rising specular light rather than invented bars or chart values.
  const BAR_LIGHTS = [[82, 757, 838], [224, 690, 811], [326, 638, 776],
    [418, 579, 749], [485, 528, 730], [517, 488, 713], [566, 448, 694],
    [620, 402, 677], [658, 382, 662], [695, 338, 647], [721, 294, 632],
    [756, 250, 616], [798, 220, 600], [841, 164, 579]];
  function barLight(ctx, s) {
    const photoScale = WIDTH / 1672;
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    BAR_LIGHTS.forEach(([x0, top0, floor0], k) => {
      const rise = smooth((s.t - .35 - k * .17) / .62);
      if (rise === 0) return;
      const x = x0 * photoScale, top = top0 * photoScale, floor = floor0 * photoScale;
      const y = floor - (floor - top) * rise;
      const pulse = Math.exp(-Math.pow((s.t - .7 - k * .17) / .47, 2));
      ctx.strokeStyle = `rgba(255,219,155,${.20 + pulse * .43})`;
      ctx.shadowColor = '#FFB347'; ctx.shadowBlur = 9 + pulse * 9; ctx.lineWidth = 2.1;
      ctx.beginPath(); ctx.moveTo(x, floor); ctx.lineTo(x, y); ctx.stroke();
      halo(ctx, x, y, 23, .11 + pulse * .25);
      if (rise > .8) {
        ctx.beginPath(); ctx.moveTo(x - 14 * rise, top); ctx.lineTo(x + 20 * rise, top - 4);
        ctx.strokeStyle = `rgba(255,239,200,${.15 + pulse * .50})`; ctx.stroke();
      }
    });
    ctx.restore();
  }
  function drawHeroEffect(ctx, index, t, duration) {
    if (index !== 7) return null;
    const s = state(t, duration);
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, COPY_BOUNDARY, HEIGHT); ctx.clip();
    barLight(ctx, s); ribbon(ctx, s); sparks(ctx, s); arrowhead(ctx, s);
    ctx.restore();
    return { progress: s.progress, tip: { ...s.tip }, arrived: s.arrived };
  }
  drawHeroEffect.geometry = (index, t, duration) => index === 7 ? state(t, duration) : null;
  global.drawHeroEffect = drawHeroEffect;
})(window);
