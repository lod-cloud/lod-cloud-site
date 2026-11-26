// The interactive LOD cloud (cloud/index.html, #107).
//
// Loads the diagram drawn by lod-cloud-draw (clouds/<stem>.svg) and puts it in the page, without
// its own script and style. Each dataset is a <g> holding a <circle> whose <title> is the
// identifier and an <a> to the dataset page; each link is a <line> with sourceId and targetId
// naming the <g> ids. The dataset whose record has the link is targetId and the one it links to
// is sourceId (checked against the records). cloud/datasets.json gives each identifier its
// title, domain, page URL and availability.
(function () {
  "use strict";
  var C = window.LOD_CLOUD;
  var $ = function (id) { return document.getElementById(id); };
  var view = $("cloud-view"), info = $("cloud-info"), statusEl = $("cloud-status");
  var params = new URLSearchParams(location.search);
  var domainInfo = C.domains.filter(function (d) { return d.key === params.get("domain"); })[0] || null;
  var REDUCED_MOTION = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var svg, full, vb;                 // the diagram, its whole extent and the current viewBox
  var nodes = [], byId = {}, byLabel = {};
  var active = {};                   // domain key => shown
  var hideUnavailable = false;
  var selected = null, touched = [];

  function status(text) { statusEl.textContent = text; }

  // The view fills the window below the toolbar (the menu above it wraps on narrow screens)
  function sizeView() {
    var top = view.getBoundingClientRect().top + window.scrollY;
    var h = window.innerHeight - top - 48;
    view.style.height = Math.round(h >= window.innerHeight * 0.6 ? h : window.innerHeight * 0.8) + "px";
  }
  sizeView();
  window.addEventListener("resize", sizeView);
  window.addEventListener("load", sizeView);   // the CDN stylesheets can change the layout above

  // ---- the diagram selector: each subcloud is its own SVG ----
  $("cloud-select").value = domainInfo ? domainInfo.key : "";
  $("cloud-select").addEventListener("change", function () {
    var p = new URLSearchParams();
    if (this.value) p.set("domain", this.value);
    location.search = p.toString();
  });

  // ---- loading ----
  function fetchText(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ": HTTP " + r.status);
      if (!r.body || !r.body.getReader) return r.text();
      var reader = r.body.getReader(), chunks = [], bytes = 0;
      function pump() {
        return reader.read().then(function (x) {
          if (x.done) return new Blob(chunks).text();
          chunks.push(x.value); bytes += x.value.length;
          status("Loading the diagram… " + (bytes / 1048576).toFixed(1) + " MB");
          return pump();
        });
      }
      return pump();
    });
  }

  status("Loading the diagram…");
  var stem = domainInfo ? domainInfo.stem : "lod-cloud";
  $("cloud-file").href = C.clouds + stem + ".svg";
  Promise.all([
    fetchText(C.clouds + stem + ".svg"),
    fetch(C.datasets).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; })
  ]).then(function (x) { setup(x[0], x[1]); }).catch(function (e) {
    status("");
    var p = document.createElement("p");
    p.className = "alert alert-danger m-3";
    p.textContent = "The diagram could not be loaded: " + (e.message || e);
    view.replaceChildren(p);
  });

  function setup(text, meta) {
    var doc = new DOMParser().parseFromString(text, "image/svg+xml");
    if (doc.getElementsByTagName("parsererror").length) throw new Error("the diagram is not valid SVG");
    svg = document.importNode(doc.documentElement, true);
    // Our own behaviour and styles replace the diagram's (its CSS would apply to the whole page)
    Array.prototype.forEach.call(svg.querySelectorAll("script, style, foreignObject"), function (el) { el.remove(); });
    Array.prototype.forEach.call(svg.querySelectorAll("*"), function (el) {
      for (var i = el.attributes.length - 1; i >= 0; i--) {
        if (/^on/i.test(el.attributes[i].name)) el.removeAttribute(el.attributes[i].name);
      }
    });

    var vbAttr = (svg.getAttribute("viewBox") || "").trim().split(/[\s,]+/).map(Number);
    full = vbAttr.length === 4 && vbAttr.every(isFinite)
      ? { x: vbAttr[0], y: vbAttr[1], w: vbAttr[2], h: vbAttr[3] }
      : { x: 0, y: 0, w: parseFloat(svg.getAttribute("width")) || 1000, h: parseFloat(svg.getAttribute("height")) || 1000 };
    svg.removeAttribute("width"); svg.removeAttribute("height");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", (domainInfo ? domainInfo.label + " subcloud" : "The Linked Open Data Cloud") + " diagram");

    // Datasets
    var byNum = {};
    Array.prototype.forEach.call(svg.querySelectorAll("circle"), function (circle) {
      var g = circle.parentNode, title = circle.querySelector("title");
      if (!title || !g.getAttribute("id")) return;
      var id = title.textContent.trim(), m = meta[id];
      var node = {
        id: id, g: g, circle: circle, out: [], in: [], lines: [],
        title: m ? m[0] : id, domain: m ? m[1] : null,
        url: m ? m[2] : null, unavailable: !!(m && m[3])
      };
      byNum[g.getAttribute("id")] = node;
      g.removeAttribute("id");             // numeric ids; do not let them clash with the page's
      g.classList.add("node-g");
      g.__node = node;
      if (node.unavailable) g.classList.add("unavailable");
      var a = g.querySelector("a");
      if (a) {
        if (node.url) a.setAttribute("href", node.url); else a.removeAttribute("href");
        a.removeAttribute("target");
        a.removeAttributeNS("http://www.w3.org/1999/xlink", "href");
      }
      node.index = nodes.length;
      nodes.push(node);
      byId[id] = node;
    });

    // Links
    var linkCount = 0;
    Array.prototype.forEach.call(svg.querySelectorAll("line"), function (line) {
      // s links to t
      var s = byNum[line.getAttribute("targetId")], t = byNum[line.getAttribute("sourceId")];
      if (!s || !t) return;
      line.__s = s; line.__t = t;
      s.lines.push(line);
      if (t !== s) {
        t.lines.push(line);
        if (s.out.indexOf(t) < 0) { s.out.push(t); t.in.push(s); linkCount++; }
      }
    });

    // The domain a dataset is drawn in: its colour. lod-cloud-draw colours the records without a
    // domain too (218 of them in 2026-11), so the record's domain alone would leave them unfiltered.
    var votes = {};
    nodes.forEach(function (n) {
      n.fill = (n.circle.getAttribute("fill") || "").toLowerCase();
      if (!n.domain) return;
      var v = votes[n.fill] = votes[n.fill] || {};
      v[n.domain] = (v[n.domain] || 0) + 1;
    });
    var colourDomain = {};
    Object.keys(votes).forEach(function (f) {
      colourDomain[f] = Object.keys(votes[f]).sort(function (a, b) { return votes[f][b] - votes[f][a]; })[0];
    });
    nodes.forEach(function (n) {
      n.recordDomain = n.domain;
      n.domain = colourDomain[n.fill] || n.domain;
    });

    view.replaceChildren(svg);
    vb = Object.assign({}, full);
    sizeView();
    apply();
    setupDomains();
    setupSearch();
    setupInteraction();
    status(nodes.length.toLocaleString() + " datasets, " + linkCount.toLocaleString() + " links");

    var wanted = params.get("d");
    if (wanted && byId[wanted]) select(byId[wanted], true);
  }

  // ---- domains and availability ----
  function setupDomains() {
    var box = $("cloud-domains"), counts = {}, colours = {};
    nodes.forEach(function (n) {
      if (!n.domain) return;
      counts[n.domain] = (counts[n.domain] || 0) + 1;
      if (!colours[n.domain]) colours[n.domain] = n.fill;
    });
    var chips = [];
    C.domains.forEach(function (d) {
      active[d.key] = true;
      if (!counts[d.key]) return;
      var b = document.createElement("button");
      b.type = "button"; b.className = "cloud-chip"; b.setAttribute("aria-pressed", "true");
      b.title = "Show or hide " + d.label + " (double-click: only this domain)";
      var sw = document.createElement("span");
      sw.className = "sw"; sw.style.background = colours[d.key] || "#999";
      b.append(sw, d.label + " ", Object.assign(document.createElement("span"), { className: "text-muted", textContent: counts[d.key] }));
      b.addEventListener("click", function () { active[d.key] = !active[d.key]; sync(); });
      b.addEventListener("dblclick", function () {
        C.domains.forEach(function (o) { active[o.key] = o.key === d.key; }); sync();
      });
      b.__key = d.key;
      chips.push(b);
    });
    if (chips.length > 1) {
      var all = document.createElement("button");
      all.type = "button"; all.className = "cloud-chip cloud-chip-all"; all.textContent = "All domains";
      all.addEventListener("click", function () { C.domains.forEach(function (o) { active[o.key] = true; }); sync(); });
      box.replaceChildren.apply(box, chips.concat([all]));
    } else {
      box.replaceChildren();
    }
    function sync() {
      chips.forEach(function (b) { b.setAttribute("aria-pressed", String(!!active[b.__key])); });
      applyFilter();
    }
    $("cloud-unavailable").addEventListener("change", function () { hideUnavailable = this.checked; applyFilter(); });
  }

  function isOff(n) { return (n.domain && !active[n.domain]) || (hideUnavailable && n.unavailable); }

  function applyFilter() {
    nodes.forEach(function (n) { n.off = isOff(n); n.g.classList.toggle("off", n.off); });
    Array.prototype.forEach.call(svg.querySelectorAll("line"), function (l) {
      if (l.__s) l.classList.toggle("off", l.__s.off || l.__t.off);
    });
    if (selected && selected.off) deselect();
    else if (selected) showInfo(selected);   // the lists leave out hidden datasets
  }

  // ---- search ----
  function setupSearch() {
    var list = $("cloud-names"), seen = {};
    var sorted = nodes.slice().sort(function (a, b) { return a.title.localeCompare(b.title); });
    sorted.forEach(function (n) { seen[n.title] = (seen[n.title] || 0) + 1; });
    var options = sorted.map(function (n) {
      var label = seen[n.title] > 1 ? n.title + " (" + n.id + ")" : n.title;
      byLabel[label] = n;
      var o = document.createElement("option");
      o.value = label;
      return o;
    });
    list.replaceChildren.apply(list, options);

    var q = $("cloud-q");
    function find() {
      var text = q.value.trim(), lower = text.toLowerCase();
      if (!text) return;
      var n = byLabel[text] || byId[text];
      if (!n) {
        var starts = null, contains = null;
        for (var i = 0; i < sorted.length && !starts; i++) {
          var t = sorted[i].title.toLowerCase(), id = sorted[i].id.toLowerCase();
          if (t.indexOf(lower) === 0 || id.indexOf(lower) === 0) starts = sorted[i];
          else if (!contains && (t.indexOf(lower) >= 0 || id.indexOf(lower) >= 0)) contains = sorted[i];
        }
        n = starts || contains;
      }
      if (!n) { status("No dataset in this diagram matches “" + text + "”"); return; }
      if (n.off) {   // show it rather than refuse
        if (n.domain) active[n.domain] = true;
        if (hideUnavailable && n.unavailable) { hideUnavailable = false; $("cloud-unavailable").checked = false; }
        Array.prototype.forEach.call(document.querySelectorAll(".cloud-chip[aria-pressed]"), function (b) {
          b.setAttribute("aria-pressed", String(!!active[b.__key]));
        });
        applyFilter();
      }
      select(n, true);
    }
    $("cloud-search").addEventListener("submit", function (e) { e.preventDefault(); find(); });
    // Picking from the datalist fires "input" with the full value
    q.addEventListener("input", function () { if (byLabel[q.value]) find(); });
  }

  // ---- highlighting and selection ----
  function clearHighlight() {
    touched.forEach(function (el) { el.classList.remove("hl", "hl-self", "hl-in", "hl-out"); });
    touched = [];
    if (svg) svg.classList.remove("focus");
  }

  function highlight(node) {
    clearHighlight();
    svg.classList.add("focus");
    mark(node.g, "hl"); mark(node.g, "hl-self");
    node.lines.forEach(function (l) {
      if (l.__s === node) { mark(l, "hl-out"); mark(l.__t.g, "hl"); }
      if (l.__t === node) { mark(l, "hl-in"); mark(l.__s.g, "hl"); }
    });
  }
  function mark(el, cls) { el.classList.add(cls); touched.push(el); }

  function select(node, focus) {
    selected = node;
    highlight(node);
    showInfo(node);
    if (focus) zoomTo(node);
    var p = new URLSearchParams(location.search);
    p.set("d", node.id);
    history.replaceState(null, "", "?" + p.toString());
  }

  function deselect() {
    selected = null;
    hovered = null;
    clearHighlight();
    info.hidden = true;
    var p = new URLSearchParams(location.search);
    p.delete("d");
    var s = p.toString();
    history.replaceState(null, "", s ? "?" + s : location.pathname);
  }

  function el(tag, props, children) {
    var e = Object.assign(document.createElement(tag), props || {});
    (children || []).forEach(function (c) { e.append(c); });
    return e;
  }

  function linkList(heading, list) {
    var shown = list.filter(function (n) { return !n.off; })
      .sort(function (a, b) { return a.title.localeCompare(b.title); });
    var summary = el("summary", { textContent: heading + " (" + shown.length + ")" });
    if (!shown.length) return [el("div", { className: "cloud-links mt-3 text-muted", textContent: summary.textContent })];
    var MAX = 100, ul = el("ul");
    shown.slice(0, MAX).forEach(function (n) {
      var b = el("button", { type: "button", className: "linklike", textContent: n.title, title: n.id });
      b.addEventListener("click", function () { select(n, true); });
      ul.append(el("li", {}, [b]));
    });
    if (shown.length > MAX) ul.append(el("li", { className: "text-muted", textContent: "and " + (shown.length - MAX) + " more" }));
    // Long lists start closed
    return [el("details", { className: "cloud-links mt-3", open: shown.length <= 40 }, [summary, ul])];
  }

  function showInfo(node) {
    var close = el("button", { type: "button", className: "close", title: "Close (Esc)", textContent: "×" });
    close.setAttribute("aria-label", "Close");
    close.addEventListener("click", deselect);
    var dom = C.domains.filter(function (d) { return d.key === node.domain; })[0];
    var heading = el("h5", { className: "mb-1" }, [
      node.url ? el("a", { href: node.url, textContent: node.title }) : node.title]);
    var parts = [close, heading, el("div", { className: "text-muted small", textContent: node.id })];
    var badges = el("div", { className: "mt-1" });
    if (dom) {
      var sw = el("span", { className: "sw" }); sw.style.background = node.fill;
      var chip = el("span", { className: "cloud-chip cloud-chip-static" }, [sw, dom.label]);
      if (!node.recordDomain) chip.title = "The record has no domain; this is the colour the diagram gives it.";
      badges.append(chip);
    }
    if (node.unavailable) badges.append(" ", el("span", { className: "badge badge-warning", textContent: "unavailable" }));
    parts.push(badges);
    parts = parts.concat(linkList("Links to", node.out), linkList("Linked from", node.in));
    if (node.url) parts.push(el("p", { className: "mt-2 mb-0" }, [el("a", { href: node.url, textContent: "Open the dataset page →" })]));
    info.replaceChildren.apply(info, parts);
    info.hidden = false;
    info.scrollTop = 0;
  }

  // ---- zoom and pan (on the viewBox) ----
  function apply() { svg.setAttribute("viewBox", vb.x + " " + vb.y + " " + vb.w + " " + vb.h); }

  // Diagram units per screen pixel ("meet" fits the larger ratio and centres the other axis)
  function unitsPerPixel() {
    var r = view.getBoundingClientRect();
    return Math.max(vb.w / r.width, vb.h / r.height);
  }

  function toDiagram(clientX, clientY) {
    var r = view.getBoundingClientRect(), s = unitsPerPixel();
    return {
      x: vb.x + (clientX - r.left - (r.width - vb.w / s) / 2) * s,
      y: vb.y + (clientY - r.top - (r.height - vb.h / s) / 2) * s
    };
  }

  function zoomAt(factor, p) {
    var w = Math.min(Math.max(vb.w / factor, full.w / 80), full.w * 2);
    factor = vb.w / w;
    vb.x = p.x - (p.x - vb.x) / factor;
    vb.y = p.y - (p.y - vb.y) / factor;
    vb.w = w; vb.h = vb.h / factor;
    apply();
  }

  function centre() { return { x: vb.x + vb.w / 2, y: vb.y + vb.h / 2 }; }

  var animation = 0;
  function animateTo(target) {
    cancelAnimationFrame(animation);
    if (REDUCED_MOTION) { vb = target; apply(); return; }
    var from = Object.assign({}, vb), t0 = performance.now(), D = 350;
    function step(now) {
      var t = Math.min(1, (now - t0) / D), e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      ["x", "y", "w", "h"].forEach(function (k) { vb[k] = from[k] + (target[k] - from[k]) * e; });
      apply();
      if (t < 1) animation = requestAnimationFrame(step);
    }
    animation = requestAnimationFrame(step);
  }

  function fit() { animateTo(Object.assign({}, full)); }

  function zoomTo(node) {
    // The circle's centre in viewBox units (the diagram wraps everything in a scaled <g>)
    var m = svg.getScreenCTM().inverse().multiply(node.circle.getScreenCTM());
    var p = new DOMPoint(+node.circle.getAttribute("cx"), +node.circle.getAttribute("cy")).matrixTransform(m);
    var w = Math.min(vb.w, full.w / 6), h = w * vb.h / vb.w;
    animateTo({ x: p.x - w / 2, y: p.y - h / 2, w: w, h: h });
  }

  function setupInteraction() {
    var pointers = new Map(), moved = false, suppressClick = false, startX = 0, startY = 0, pinch = null;

    view.addEventListener("wheel", function (e) {
      e.preventDefault();
      cancelAnimationFrame(animation);
      var dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
      zoomAt(Math.exp(-dy * 0.0015), toDiagram(e.clientX, e.clientY));
    }, { passive: false });

    view.addEventListener("pointerdown", function (e) {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      cancelAnimationFrame(animation);
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (pointers.size === 1) { moved = false; startX = e.clientX; startY = e.clientY; }
      if (pointers.size === 2) { pinch = pinchState(); moved = true; }
    });

    view.addEventListener("pointermove", function (e) {
      var p = pointers.get(e.pointerId);
      if (!p) {   // hover
        if (!selected && e.pointerType === "mouse") hover(e.target);
        return;
      }
      if (pointers.size === 1) {
        if (!moved && Math.hypot(e.clientX - startX, e.clientY - startY) > 4) {
          moved = true;
          view.classList.add("dragging");
          view.setPointerCapture(e.pointerId);
        }
        if (moved) {
          var s = unitsPerPixel();
          vb.x -= (e.clientX - p.x) * s; vb.y -= (e.clientY - p.y) * s;
          apply();
        }
        p.x = e.clientX; p.y = e.clientY;
      } else if (pointers.size === 2) {
        p.x = e.clientX; p.y = e.clientY;
        var now = pinchState(), s2 = unitsPerPixel();
        vb.x -= (now.mx - pinch.mx) * s2; vb.y -= (now.my - pinch.my) * s2;
        if (pinch.d > 0 && now.d > 0) zoomAt(now.d / pinch.d, toDiagram(now.mx, now.my));
        else apply();
        pinch = now;
      }
    });

    function pinchState() {
      var ps = Array.from(pointers.values());
      return { mx: (ps[0].x + ps[1].x) / 2, my: (ps[0].y + ps[1].y) / 2, d: Math.hypot(ps[0].x - ps[1].x, ps[0].y - ps[1].y) };
    }

    function up(e) {
      if (!pointers.delete(e.pointerId)) return;
      if (pointers.size < 2) pinch = null;
      if (pointers.size === 1) {   // one finger left after a pinch: carry on panning from where it is
        var rest = Array.from(pointers.values())[0]; startX = rest.x; startY = rest.y;
      }
      if (pointers.size === 0) {
        view.classList.remove("dragging");
        if (moved) { suppressClick = true; setTimeout(function () { suppressClick = false; }, 0); }
      }
    }
    view.addEventListener("pointerup", up);
    view.addEventListener("pointercancel", up);
    view.addEventListener("pointerleave", function (e) { if (e.pointerType === "mouse" && !selected) clearHighlight(); });

    view.addEventListener("click", function (e) {
      if (suppressClick) { e.preventDefault(); e.stopPropagation(); return; }
      var g = e.target.closest && e.target.closest(".node-g");
      if (g) {
        if (e.ctrlKey || e.metaKey || e.shiftKey) return;   // open the dataset page as the link would
        e.preventDefault();
        var n = nodeOf(g);
        if (n === selected) deselect(); else select(n, false);
      } else if (selected) {
        deselect();
      }
    }, true);

    view.addEventListener("keydown", function (e) {
      if (e.target !== view) return;
      var step = 0.15, handled = true;
      switch (e.key) {
        case "ArrowLeft": vb.x -= vb.w * step; apply(); break;
        case "ArrowRight": vb.x += vb.w * step; apply(); break;
        case "ArrowUp": vb.y -= vb.h * step; apply(); break;
        case "ArrowDown": vb.y += vb.h * step; apply(); break;
        case "+": case "=": zoomAt(1.4, centre()); break;
        case "-": case "_": zoomAt(1 / 1.4, centre()); break;
        case "0": fit(); break;
        case "Escape": if (selected) deselect(); else handled = false; break;
        default: handled = false;
      }
      if (handled) e.preventDefault();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && selected && e.target !== view && !/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) deselect();
    });

    Array.prototype.forEach.call(document.querySelectorAll("[data-zoom]"), function (b) {
      b.addEventListener("click", function () {
        var z = b.getAttribute("data-zoom");
        if (z === "fit") fit(); else zoomAt(z === "in" ? 1.4 : 1 / 1.4, centre());
      });
    });
  }

  var hovered = null;
  function hover(target) {
    var g = target.closest && target.closest(".node-g");
    var n = g ? nodeOf(g) : null;
    if (n === hovered) return;
    hovered = n;
    if (n) highlight(n); else clearHighlight();
  }

  function nodeOf(g) { return g.__node || null; }
})();
