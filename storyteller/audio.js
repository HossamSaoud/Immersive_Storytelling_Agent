() => {
  // Sound and music are synthesised in the browser (Web Audio): no files, no keys, no tokens.
  // The director model picks the mood and the ambience; render.py puts them on .stage as data-mood / data-sound.
  let ctx, bus, ambience = null, music = null, now = {};

  // mood -> [semitone scale, root Hz, ms between notes, oscillator type, volume]
  const MUSIC = {
    calm: [[0, 2, 4, 7, 9], 220, 2200, "sine", 0.05], wonder: [[0, 2, 4, 6, 7, 9, 11], 262, 1300, "triangle", 0.05],
    mystery: [[0, 1, 4, 5, 7, 8], 196, 1800, "sine", 0.05], tense: [[0, 1, 3, 6, 7], 147, 800, "triangle", 0.06],
    danger: [[0, 1, 3, 5, 6, 8], 110, 420, "sawtooth", 0.04], melancholy: [[0, 2, 3, 5, 7, 8, 10], 196, 2400, "sine", 0.05],
    joy: [[0, 2, 4, 7, 9], 330, 500, "triangle", 0.06], triumph: [[0, 4, 7, 11, 12], 262, 750, "triangle", 0.06],
  };

  const gain = (v, to = bus) => { const g = ctx.createGain(); g.gain.value = v; g.connect(to); return g; };
  const noise = (to) => {
    const b = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const s = ctx.createBufferSource(); s.buffer = b; s.loop = true; s.start(); return s;
  };
  const filtered = (type, freq, q, to) => { const f = ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q; f.connect(to); return f; };
  const lfo = (rate, depth, param) => { const o = ctx.createOscillator(), g = ctx.createGain(); o.frequency.value = rate; g.gain.value = depth; o.connect(g); g.connect(param); o.start(); return o; };
  const tone = (type, freq, to, v = 1) => { const o = ctx.createOscillator(); o.type = type; o.frequency.value = freq; o.connect(gain(v, to)); o.start(); return o; };
  const blip = (freq, to, v, dur) => {  // one short decaying note
    const o = ctx.createOscillator(), g = ctx.createGain(), t = ctx.currentTime;
    o.frequency.value = freq; g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + 0.03); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(to); o.start(t); o.stop(t + dur + 0.1);
  };

  // each recipe builds its sound into `out` and returns [things to stop, timers to clear]
  const RECIPES = {
    wind: (out) => { const n = noise(), f = filtered("bandpass", 500, 0.6, out); n.connect(f); return [[n, lfo(0.07, 300, f.frequency)], []]; },
    rain: (out) => { const n = noise(); n.connect(filtered("highpass", 1800, 0.5, gain(0.5, out))); return [[n], []]; },
    sea: (out) => { const n = noise(), g = gain(0.5, out); n.connect(filtered("lowpass", 600, 0.5, g)); return [[n, lfo(0.11, 0.35, g.gain)], []]; },
    fire: (out) => {
      const n = noise(), g = gain(0.25, out); n.connect(filtered("lowpass", 700, 0.5, g));
      const t = setInterval(() => blip(800 + Math.random() * 2500, out, 0.06, 0.05), 160); return [[n], [t]];
    },
    forest: (out) => {
      const n = noise(), f = filtered("bandpass", 350, 0.7, gain(0.35, out)); n.connect(f);
      const t = setInterval(() => { if (Math.random() < 0.4) blip(2500 + Math.random() * 1500, out, 0.04, 0.12); }, 700); return [[n, lfo(0.05, 150, f.frequency)], [t]];
    },
    cave: (out) => {
      const o = tone("sine", 55, out, 0.5), t = setInterval(() => { if (Math.random() < 0.5) blip(900 + Math.random() * 500, out, 0.08, 0.35); }, 1400); return [[o], [t]];
    },
    machinery: (out) => { const a = tone("sawtooth", 50, filtered("lowpass", 220, 1, out), 0.5), b = tone("square", 100, filtered("lowpass", 300, 1, out), 0.1); return [[a, b], []]; },
    space: (out) => { const f = filtered("lowpass", 400, 1, out); const a = tone("sine", 55, f, 0.6), b = tone("sine", 55.7, f, 0.6); return [[a, b, lfo(0.05, 150, f.frequency)], []]; },
    crowd: (out) => { const n = noise(); n.connect(filtered("bandpass", 700, 0.8, gain(0.25, out))); return [[n], []]; },
  };

  const play = (build) => {  // returns a handle whose stop() fades the sound out and cleans up
    const out = gain(0, bus); out.gain.linearRampToValueAtTime(1, ctx.currentTime + 2);
    const [nodes, timers] = build(out);
    return { stop() { out.gain.linearRampToValueAtTime(0, ctx.currentTime + 2); timers.forEach(clearInterval); setTimeout(() => nodes.forEach((n) => n.stop()), 2500); } };
  };

  const thump = (out, v, t0) => {  // one soft low drum hit
    const o = ctx.createOscillator(), g = ctx.createGain(), t = ctx.currentTime + t0;
    o.frequency.setValueAtTime(140, t); o.frequency.exponentialRampToValueAtTime(45, t + 0.2);  // starts higher so laptop speakers still carry it
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.3);
    o.connect(g); g.connect(out); o.start(t); o.stop(t + 0.4);
  };

  // Tense: a low unresolved drone (a minor second and a tritone grind against each other), a heartbeat, a faint high squeal now and then.
  const startTense = () => play((out) => {
    const low = filtered("lowpass", 320, 0.8, out);
    const drone = [55, 58.3, 77.8, 110, 116.6].map((f, i) => tone("sine", f, low, [0.5, 0.5, 0.25, 0.15, 0.15][i]));
    const swell = lfo(0.09, 0.15, out.gain);
    const beat = setInterval(() => { thump(out, 0.7, 0); thump(out, 0.4, 0.24); }, 1050);
    const squeal = setInterval(() => { if (Math.random() < 0.5) blip(1480 + Math.random() * 60, out, 0.012, 3); }, 4500);
    return [[...drone, swell], [beat, squeal]];
  });

  const startMusic = (mood) => {
    if (mood === "tense") return startTense();
    const [scale, root, every, wave, vol] = MUSIC[mood] || MUSIC.mystery;
    return play((out) => {
      const pad = filtered("lowpass", 700, 0.7, out);
      const voices = [0, scale[2], scale[4 % scale.length]].map((s) => tone("sine", (root / 2) * 2 ** (s / 12), pad, vol * 0.8));
      const t = setInterval(() => {
        const note = scale[Math.floor(Math.random() * scale.length)], octave = Math.random() < 0.3 ? 2 : 1;
        blip(root * octave * 2 ** (note / 12), out, vol, every / 1000 * 1.6);
      }, every);
      return [voices, [t]];
    });
  };

  window.echoes = (on) => {
    const stage = document.querySelector(".stage");
    if (!on || !stage) { ambience?.stop(); music?.stop(); ambience = music = null; now = {}; return; }
    ctx = ctx || new AudioContext(); bus = bus || gain(0.5, ctx.destination);
    ctx.resume();
    const { mood, sound } = stage.dataset;
    if (mood !== now.mood) { music?.stop(); music = startMusic(mood); }
    if (sound !== now.sound) { ambience?.stop(); ambience = RECIPES[sound] ? play(RECIPES[sound]) : null; }
    now = { mood, sound };
  };
}
