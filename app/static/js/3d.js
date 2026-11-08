/* Maagi Pickle — 3D interactions: card tilt, hero parallax, scroll reveal, product ring.
   Pure vanilla JS, no dependencies. Every feature degrades to the flat design if it is not supported. */
(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var finePointer = window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  // ---------- Scroll reveal ----------
  function initReveal() {
    var items = [].slice.call(document.querySelectorAll("[data-reveal]"));
    if (!items.length) return;
    if (reduce || !("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.classList.add("in"); });
      return;
    }
    // stagger siblings inside the same parent
    var groups = new Map();
    items.forEach(function (el) {
      var list = groups.get(el.parentNode) || [];
      el.style.setProperty("--reveal-delay", Math.min(list.length * 90, 450) + "ms");
      list.push(el);
      groups.set(el.parentNode, list);
    });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    items.forEach(function (el) { io.observe(el); });
  }

  // ---------- Tilt + glare (mouse only) ----------
  function initTilt() {
    if (reduce || !finePointer) return;
    document.querySelectorAll("[data-tilt]").forEach(function (el) {
      var max = parseFloat(el.getAttribute("data-tilt")) || 9;
      var raf = null;
      el.addEventListener("pointermove", function (ev) {
        if (ev.pointerType && ev.pointerType !== "mouse") return;
        var r = el.getBoundingClientRect();
        var px = (ev.clientX - r.left) / r.width;
        var py = (ev.clientY - r.top) / r.height;
        if (raf) cancelAnimationFrame(raf);
        raf = requestAnimationFrame(function () {
          el.classList.add("is-tilting");
          el.style.setProperty("--ry", ((px - 0.5) * 2 * max).toFixed(2) + "deg");
          el.style.setProperty("--rx", ((0.5 - py) * 2 * max).toFixed(2) + "deg");
          el.style.setProperty("--mx", (px * 100).toFixed(1) + "%");
          el.style.setProperty("--my", (py * 100).toFixed(1) + "%");
        });
      });
      el.addEventListener("pointerleave", function () {
        if (raf) cancelAnimationFrame(raf);
        el.classList.remove("is-tilting");
        el.style.setProperty("--rx", "0deg");
        el.style.setProperty("--ry", "0deg");
      });
    });
  }

  // ---------- Hero parallax ----------
  function initHero() {
    var hero = document.querySelector(".hero");
    var stage = document.querySelector(".hero-stage");
    if (!hero || !stage || reduce || !finePointer) return;
    hero.addEventListener("pointermove", function (ev) {
      var r = hero.getBoundingClientRect();
      var x = (ev.clientX - r.left) / r.width - 0.5;
      var y = (ev.clientY - r.top) / r.height - 0.5;
      stage.style.setProperty("--sry", (x * 16).toFixed(2) + "deg");
      stage.style.setProperty("--srx", (-y * 12).toFixed(2) + "deg");
    });
    hero.addEventListener("pointerleave", function () {
      stage.style.setProperty("--sry", "0deg");
      stage.style.setProperty("--srx", "0deg");
    });
  }

  // ---------- 3D product ring ----------
  function initRing() {
    var stage = document.querySelector(".range-stage");
    if (!stage) return;
    var ring = stage.querySelector(".range-ring");
    var items = [].slice.call(ring.querySelectorAll(".range-item"));
    var n = items.length;
    if (n < 3) { stage.closest(".range-section").style.display = "none"; return; }

    var current = 0, timer = null, paused = false;
    var narrow = function () { return window.innerWidth < 576; };

    // Coverflow layout: works for any number of products (a true cylinder
    // collapses edge-on when there are only a few cards).
    function render() {
      var gap = narrow() ? 120 : 220, depth = 150, tilt = 32;
      items.forEach(function (it, i) {
        var d = i - (((current % n) + n) % n);
        if (d > n / 2) d -= n;
        if (d < -n / 2) d += n;
        var a = Math.abs(d);
        it.style.transform = "translateX(" + (d * gap) + "px) translateZ(" + (-a * depth) + "px) rotateY(" + (-d * tilt) + "deg)";
        it.style.opacity = a > 2 ? 0 : 1;
        it.style.zIndex = 10 - a;
        it.style.pointerEvents = a > 2 ? "none" : "auto";
        it.classList.toggle("is-front", d === 0);
      });
    }
    function go(delta) { current += delta; render(); }

    stage.parentNode.querySelectorAll("[data-ring]").forEach(function (b) {
      b.addEventListener("click", function () { go(b.getAttribute("data-ring") === "next" ? 1 : -1); restart(); });
    });

    // drag / swipe
    var startX = null;
    stage.addEventListener("pointerdown", function (e) { startX = e.clientX; });
    window.addEventListener("pointerup", function (e) {
      if (startX === null) return;
      var dx = e.clientX - startX; startX = null;
      if (Math.abs(dx) > 40) { go(dx < 0 ? 1 : -1); restart(); }
    });
    stage.addEventListener("mouseenter", function () { paused = true; });
    stage.addEventListener("mouseleave", function () { paused = false; });

    function restart() {
      if (timer) clearInterval(timer);
      if (reduce) return;
      timer = setInterval(function () { if (!paused && !document.hidden) go(1); }, 3800);
    }
    window.addEventListener("resize", render);
    render(); restart();
  }

  function boot() { initReveal(); initTilt(); initHero(); initRing(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
