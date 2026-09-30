// Shared, seek-safe motion helpers for the "Humain 10/10" scenes.
// Every helper only adds tweens to a paused GSAP timeline: no clocks,
// no randomness, no callbacks — any frame is reproducible from time alone.
(function () {
  const T = window.HF_TIMING;

  // Closed-form damped spring (unit step response) used as a GSAP ease.
  // zeta < 1 overshoots; omega is the natural frequency in rad/s over `dur` seconds.
  function spring(zeta, omega, dur) {
    const wd = omega * Math.sqrt(1 - zeta * zeta);
    const end = 1 - Math.exp(-zeta * omega * dur) * (Math.cos(wd * dur) + ((zeta * omega) / wd) * Math.sin(wd * dur));
    return function (p) {
      const t = p * dur;
      const x = 1 - Math.exp(-zeta * omega * t) * (Math.cos(wd * t) + ((zeta * omega) / wd) * Math.sin(wd * t));
      return p >= 1 ? 1 : x / end;
    };
  }

  const scene = (id) => T.scenes[id];
  const vo = (id, i, off) => T.scenes[id].vo[i][0] + (off || 0);
  const beat = (n) => n * T.beat;

  // Mask reveal: `.m > .ln` lines slide up out of an overflow:hidden mask.
  function reveal(tl, sel, at, opts) {
    const o = Object.assign({ dur: 0.62, stagger: 0.09 }, opts);
    tl.fromTo(sel, { yPercent: 160 }, { yPercent: 0, duration: o.dur, ease: "expo.out", stagger: o.stagger }, at);
  }

  // Number Ticker (odometer). `el` holds one `.col` per digit, built by `buildTicker`.
  // All columns scroll in lockstep; a column only visibly rolls when its digit changes.
  function buildTicker(el, to) {
    const digits = String(to).length;
    el.innerHTML = "";
    for (let k = digits - 1; k >= 0; k--) {
      const col = document.createElement("span");
      col.className = "col";
      col.setAttribute("data-layout-allow-overflow", "true");
      col.setAttribute("data-layout-allow-overlap", "true"); // hidden digits are clipped by the column
      const strip = document.createElement("span");
      strip.className = "strip";
      for (let v = 0; v <= to; v++) {
        const d = document.createElement("span");
        d.setAttribute("data-layout-allow-overlap", "true");
        const lead = v < Math.pow(10, k) && k > 0;
        d.textContent = lead ? "" : String(Math.floor(v / Math.pow(10, k)) % 10);
        strip.appendChild(d);
      }
      col.appendChild(strip);
      el.appendChild(col);
    }
    return el.querySelectorAll(".strip");
  }
  function ticker(tl, el, to, at, dur) {
    const strips = buildTicker(el, to);
    const pct = (100 * to) / (to + 1);
    tl.fromTo(strips, { yPercent: 0 }, { yPercent: -pct, duration: dur, ease: "power3.out" }, at);
  }

  // Text Rotate: per-character spring swap between stacked words.
  // `box` contains one `.rw` per word (absolutely stacked); chars are split here.
  function splitChars(word) {
    const txt = word.textContent.trim();
    word.textContent = "";
    txt.split(" ").forEach((w, i) => {
      if (i) word.appendChild(document.createTextNode(" "));
      const g = document.createElement("span");
      g.className = "wd";
      g.style.display = "inline-block";
      g.style.whiteSpace = "nowrap";
      for (const ch of w) {
        const s = document.createElement("span");
        s.className = "ch";
        s.style.display = "inline-block";
        s.textContent = ch;
        g.appendChild(s);
      }
      word.appendChild(g);
    });
    return word.querySelectorAll(".ch");
  }
  function rotate(tl, box, times, opts) {
    const o = Object.assign({ first: true }, opts);
    const words = Array.from(box.querySelectorAll(".rw"));
    const chars = words.map(splitChars);
    const ease = spring(0.62, 26, 0.5);
    words.forEach((w, i) => {
      const t = times[i];
      tl.set(w, { opacity: 1 }, t);
      if (i > 0 || o.first) {
        tl.fromTo(chars[i], { yPercent: 110, opacity: 0 }, { yPercent: 0, opacity: 1, duration: 0.5, ease, stagger: 0.022 }, t);
      }
      if (i > 0) {
        // old word leaves completely before the new one lands (no overlapping glyphs)
        tl.to(chars[i - 1], { yPercent: -110, opacity: 0, duration: 0.2, ease: "power2.in", stagger: 0.006 }, t - 0.3);
        tl.set(words[i - 1], { opacity: 0 }, t - 0.01);
      }
    });
  }

  // Border Beam: conic highlight masked to a 3px ring, travelling a finite number of laps.
  function beam(tl, el, at, until, lapDur) {
    const laps = Math.max(1, Math.floor((until - at) / lapDur));
    tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.3, ease: "none" }, at);
    tl.fromTo(el, { "--a": "0deg" }, { "--a": 360 * laps + "deg", duration: laps * lapDur, ease: "none" }, at);
  }

  window.HF10 = { spring, scene, vo, beat, reveal, ticker, rotate, beam };
})();
