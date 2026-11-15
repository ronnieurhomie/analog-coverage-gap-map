// AI assistance: Claude Code (Anthropic) and OpenAI Codex; original science results remain unchanged.
// Display only: every number comes from data/display.json or data/results_summary.json (built from results/ by scripts/).
"use strict";

const RHO = 182100; // half-width of the LOLA hillshade in metres (data/lola_84S_hillshade.json)
const CANT_SEE = ["gravity (Earth 1 g, Moon 0.17 g)", "vacuum", "regolith mechanics", "illumination and thermal environment",
  "radiation", "rocks smaller than the 30 m elevation grid"];
let D, R;
const state = { set: "K", historical: false, patch: null, sel: null };

const $ = (s) => document.querySelector(s);
const f1 = (x) => (Math.round(x * 10) / 10).toFixed(1);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const title = (s) => String(s).replace(/\b\w/g, (c) => c.toUpperCase());
const pos = (p) => ({ left: ((p.x + RHO) / (2 * RHO) * 100) + "%", top: ((RHO - p.y) / (2 * RHO) * 100) + "%" });

function featLabel(n) {
  const m = n.match(/^(slope|roughness)_(median|p90|iqr)_(\d+)m$/);
  const stat = { median: "typical slope", p90: "90th-percentile slope", iqr: "slope spread" }[m[2]];
  return m[1] === "slope" ? `${stat} at ${m[3]} m` : `median bumpiness (roughness) at ${m[3]} m`;
}
const fval = (n, v) => (n.startsWith("slope") ? f1(v) + "°" : (Math.round(v * 100) / 100).toFixed(2) + " m");

// human label first, then chips; IDs shown small
function earthLabel(id, name, set) {
  if (id === "g00094") return { name: "Morocco candidate", sub: "g00094", chips: ["Sampled"] };
  if (/^g\d+$/.test(id)) { const m = name.match(/\(([-\d.]+), ([-\d.]+)\)/); return { name: `Sampled site (${m[1]}, ${m[2]})`, sub: id, chips: ["Sampled"] }; }
  if (id.startsWith("nasa_")) return { name: title(name), sub: "", chips: ["NASA test site"] };
  if (id === "mojave_dumont") return { name: "Dumont Dunes window", sub: "also a NASA test site", chips: ["Mojave test window", "NASA test site"] };
  if (id.startsWith("mojave_")) { const m = id.match(/r(\d)_c(\d)/); return { name: id === "mojave_avawatz_negctrl" ? "Avawatz Mts window" : `Mojave test window r${m[1]} c${m[2]}`, sub: "not a known test site", chips: ["Mojave test window"] }; }
  if (id.startsWith("usgs_")) return { name: name.replace(/ \(impact crater, USGS\)$/, " impact crater"), sub: "USGS", chips: ["USGS"] };
  return { name, sub: "", chips: [set === "USGS-29" ? "USGS" : set] };
}
const chips = (l) => l.chips.map((c) => `<span class="chip">${esc(c)}</span>`).join(" ");

function zcmp(a, b) {
  const n = D.feature_names, fa = D.features[a], fb = D.features[b], sd = D.feature_sd;
  return n.map((k, i) => ({ k, a: fa[i], b: fb[i], dz: (fa[i] - fb[i]) / sd[i] }));
}

/* ---------- one comparison, its evidence, and its limits ---------- */
function example() {
  const S = D.showcase, p = D.patches.find((x) => x.id === S.patch);
  $("#ex-lede").textContent = "Morocco passes our fixed ground-shape cut-off. Even the closest site in our known list does not.";
  const card = (image, name, score, passes, alt) => `<figure class="imgcard"><img src="${image}" alt="${esc(alt)}" width="192" height="192" loading="lazy">
    <div class="scale"><i></i><span>500 m</span></div><figcaption><strong>${esc(name)}</strong>
    ${score === null ? '' : `<span class="result ${passes ? 'yes' : 'no'}">${passes ? 'Passes' : 'Does not pass'} our shape cut-off</span><span class="small">Score ${score.toFixed(3)}</span>`}</figcaption></figure>`;
  $("#trio").innerHTML = card(`img/moon/${S.patch}.png`, "Moon target", null, false, `Moon square ${S.patch}, 1.92 km on each side`) +
    card(`img/earth/${S.candidate}.png`, "Candidate: southern Morocco", S.candidate_d, true, "Morocco candidate, same physical extent") +
    card(`img/earth/${S.known_id}.png`, `Closest listed site: ${S.known_name}`, S.known_d, false, `${S.known_name}, same physical extent`);
  const f = (id, key) => D.features[id][D.feature_names.indexOf(key)];
  $("#verdict").innerHTML = `<h3>A passing score still leaves important differences.</h3><div class="tablewrap"><table>
    <thead><tr><th>Measured condition</th><th>Moon</th><th>Morocco</th></tr></thead><tbody>
    <tr><th>Steep-end slope, at 30 m</th><td>${fval('slope', f(S.patch, 'slope_p90_30m'))}</td><td>${fval('slope', f(S.candidate, 'slope_p90_30m'))}</td></tr>
    <tr><th>Bumpiness, at 480 m</th><td>${fval('roughness', f(S.patch, 'roughness_median_480m'))}</td><td>${fval('roughness', f(S.candidate, 'roughness_median_480m'))}</td></tr></tbody></table></div>
    <p>Steep-end slopes are close at 30 m. Morocco is bumpier at the largest measured scale.</p>`;
  $("#ex-foot").textContent = `Early result. Lower scores mean closer ground shape; the fixed cut-off is ${S.T.toFixed(3)}. ` +
    `The score combines 19 measurements, not just the two shown above. Known list: ${D.sets.K.label}. ` +
    `Target ${S.patch} (${Math.abs(p.lat).toFixed(3)}°S, ${Math.abs(p.lon).toFixed(3)}°W); candidate ${S.candidate}. ` +
    `Only this sampled candidate matches this target among the locations compared. Not an exhaustive Earth search; not a discovery.`;
  $("#example-data").innerHTML = `<table><thead><tr><th>Measurement</th><th>Moon</th><th>Morocco</th><th>${esc(S.known_name)}</th></tr></thead><tbody>${D.feature_names.map((n, i) => `<tr><th>${featLabel(n)}</th><td>${fval(n,D.features[S.patch][i])}</td><td>${fval(n,D.features[S.candidate][i])}</td><td>${fval(n,D.features[S.known_id][i])}</td></tr>`).join('')}</tbody></table>`;
}

/* ---------- explore ---------- */
function activeKey() { return state.historical ? "historical" : state.set; }
function legendText() {
  const k = activeKey(), s = D.sets[k];
  return `Showing: ${esc(s.label)} — ${s.covered} matched, ${s.gap} no match, of ${s.denominator} patches · ground shape, fixed cut-off d < ${D.T.toFixed(3)} · ${esc(s.nature)}.`;
}
function drawMarkers() {
  const map = $("#map"); map.querySelectorAll(".pt").forEach((b) => b.remove());
  const k = activeKey();
  D.patches.forEach((p) => {
    const cov = p.status[k], cand = (p.candidates || []).length > 0;
    const b = document.createElement("button");
    b.type = "button"; b.className = "pt " + (cov ? "covered" : "gap") + (cand ? " cand" : "");
    Object.assign(b.style, pos(p));
    b.setAttribute("aria-label", `Patch ${p.id}, ${Math.abs(p.lat).toFixed(2)}° south, ${cov ? "matched by a known site" : "no match among known sites"}${cand ? ", has a sampled candidate" : ""}`);
    b.setAttribute("aria-pressed", state.patch === p.id ? "true" : "false");
    b.addEventListener("click", () => { state.patch = p.id; state.sel = null; drawMarkers(); drawPanel(true); });
    map.appendChild(b);
  });
  $("#legend").innerHTML = legendText();
}
function items(p) {
  const k = p.known_K;
  const known = { id: k.id, ...earthLabel(k.id, k.name, k.id.startsWith("nasa_") ? "NASA test site" : "USGS"), d: k.distance, below: k.below_T };
  const nb = p.neighbours.filter((n) => n.id !== k.id).map((n) => ({ id: n.id, ...earthLabel(n.id, n.name, n.set), d: n.distance, below: n.below_T }));
  const gc = (p.candidates || []).map((c) => ({ id: c.id, ...earthLabel(c.id, D.earth_names[c.id].name, "Sampled"), d: c.distance, below: c.below_T, beyondK: c.beyond_K }));
  return { known, nb, gc, all: [known, ...nb, ...gc] };
}
function analogCard(moonId, it) {
  const z = zcmp(moonId, it.id), i90 = D.feature_names.indexOf("slope_p90_30m");
  const sim = z.filter((x) => Math.abs(x.dz) <= 1).sort((x, y) => Math.abs(x.dz) - Math.abs(y.dz));
  const diff = [...z].sort((x, y) => Math.abs(y.dz) - Math.abs(x.dz)).slice(0, 3).filter((x) => Math.abs(x.dz) > 1);
  const li = (x) => `<li>${featLabel(x.k)}: Moon ${fval(x.k, x.a)}, Earth ${fval(x.k, x.b)}</li>`;

  return `<div class="card">
    <h4>Most similar measurements <span class="small">(within one pooled standard deviation)</span></h4>
    <ul>${sim.length ? sim.slice(0, 3).map(li).join("") : "<li>none of the 19 features</li>"}</ul>
    ${sim.length > 3 ? `<details><summary>Show all ${sim.length} similar measurements</summary><ul>${sim.slice(3).map(li).join("")}</ul></details>` : ""}
    <h4>Largest differences</h4>
    <ul>${diff.length ? diff.map((x) => `<li>${featLabel(x.k)}: Moon ${fval(x.k, x.a)} vs Earth ${fval(x.k, x.b)} (${f1(Math.abs(x.dz))} pooled standard deviations)</li>`).join("") : "<li>no feature differs by more than one pooled standard deviation</li>"}</ul>
    <h4>What elevation data cannot show</h4><ul>${CANT_SEE.map((c) => `<li>${c}</li>`).join("")}</ul>
    <h4>What to check before field use</h4><ul><li>The 90th-percentile slope at 30 m is ${fval("slope", z[i90].b)} on Earth and ${fval("slope", z[i90].a)} on the Moon.</li><li>Check real ground cover, soil, rock size, access and permission. No vehicle testing has been done here by this project.</li></ul></div>`;
}
function drawPanel(focus) {
  const p = D.patches.find((x) => x.id === state.patch); if (!p) return;
  const k = activeKey(), s = D.sets[k], cov = p.status[k];
  const its = items(p);
  const it = its.all.find((x) => x.id === state.sel) || its.all[0]; state.sel = it.id;
  const btn = (x) => `<li><button type="button" data-id="${esc(x.id)}" aria-pressed="${x.id === it.id}"><span>${esc(x.name)}</span>
      ${chips(x)}${x.beyondK ? ' <span class="chip">adds a match beyond the known-site list</span>' : ""}<span class="dv">d = ${x.d.toFixed(2)}</span></button></li>`;
  $("#panel").innerHTML = `
    <h3>Selected Moon square <span class="id">(${p.id})</span></h3><span class="id">${Math.abs(p.lat).toFixed(3)}°S, ${p.lon.toFixed(2)}°</span>
    <p class="small" style="margin:0"><span class="pill ${cov ? "matched" : "nomatch"}">${cov ? "matched" : "no match"}</span> among ${esc(s.label)}</p>
    <p class="verdictline ${it.below ? "" : "out"}"><strong>${esc(it.name)}: d = ${it.d.toFixed(3)}</strong> —
      ${it.below ? "passes our ground-shape cut-off (look-alike)" : "does not pass our cut-off (comparison only)"}</p>
    <h4 style="margin:16px 0 0">Nearest known site in the full list</h4><ul class="nb">${btn(its.known)}</ul>
    ${its.gc.length ? `<h4 style="margin:8px 0 0">Sampled look-alikes <span class="small">(early results)</span></h4><ul class="nb">${its.gc.map(btn).join("")}</ul>` : ""}
    <div class="pair">
      <figure style="margin:0"><img src="img/moon/${p.id}.png" alt="Shaded relief of Moon patch ${p.id}, 1.92 km square" width="192" height="192">
        <div class="scale"><i></i><span>500 m</span></div><div class="cap">Moon ${p.id}</div></figure>
      <figure style="margin:0"><img src="img/earth/${esc(it.id)}.png" alt="Shaded relief of the Earth window ${esc(it.name)}, 1.92 km square" width="192" height="192">
        <div class="scale"><i></i><span>500 m</span></div><div class="cap">Earth: ${esc(it.name)}</div></figure>
    </div>
    <p class="small">Same 1.92 km square, 30 m grid and shading. Shading is simulated; actual illumination is not compared.</p>
    <details class="disc"><summary>Measurements, other windows and limits</summary><div class="inner">
    ${analogCard(p.id, it)}<p class="small">${esc(D.neighbour_pool)}</p><ul class="nb">${its.nb.map(btn).join("")}</ul></div></details>`;
  $("#panel").querySelectorAll(".nb button").forEach((b) => b.addEventListener("click", () => { state.sel = b.dataset.id; drawPanel(false); }));
  if (focus) $("#panel").focus({ preventScroll: true });
}

/* ---------- results ---------- */
function results() {
  const bar = (k, small, main) => { const s = D.sets[k];
    return `<div class="barrow"><div class="bl"><span>${main ? "<strong>" : ""}${esc(s.label)}${main ? "</strong>" : ""} <span class="small">· ${esc(s.nature)}</span></span>
      <span class="small"><strong>${s.covered}</strong> matched · <strong>${s.gap}</strong> no match · of ${s.denominator}</span></div>
      <div class="bar ${small ? "small" : ""}" role="img" aria-label="${s.covered} of ${s.denominator} matched, ${s.gap} no match">
      <span class="cov" style="width:${s.covered / s.denominator * 100}%"></span><span class="gap" style="width:${s.gap / s.denominator * 100}%"></span></div></div>`; };
  $("#bars").innerHTML = bar("K", false, true) +
    `<p>Of ${D.sets.K.denominator} sampled Moon squares, ${D.sets.K.covered} match a listed site and ${D.sets.K.gap} do not.</p>
    <p><strong>Sampling ${R.global.processed} land locations adds candidates for ${D.clarity.random_additional_count} of the ${D.sets.K.gap} unmatched squares.</strong></p>
    <p class="small">Ground shape only, under the same fixed cut-off. These are square counts, not lunar area shares.</p>`;
  $("#other-bars").innerHTML = bar("union", true) + bar("historical", true) +
    `<p>${D.clarity.mojave_additional_count} of the ${D.sets.K.gap} also match a Mojave test-grid window outside the known-site list. This overlaps the sample result; do not add the counts.</p>`;
  const c = R.candidate, rows = D.increment.candidates;
  const top = rows.filter((r) => r.N_beyond_K > 0).sort((a, b) => (a.id === "g00094" ? -1 : b.id === "g00094" ? 1 : b.N_beyond_K - a.N_beyond_K));
  $("#cands").innerHTML = top.map((r) => {
    const flag = r.novelty === "Unverified" ? '<span class="pill unverified">Unverified</span>' : `<span class="pill neutral">${esc(r.novelty)}</span>`;
    const checked = r.id === "g00094";
    return `<div class="cardx"><div class="big">+${r.N_beyond_K}</div>
      <p><strong>${r.id === "g00094" ? "Morocco candidate" : `Sampled site (${r.lat.toFixed(2)}, ${r.lon.toFixed(2)})`}</strong> <span class="id">${r.id}</span></p>
      <p>${flag} ${checked ? '<span class="chip">literature + imagery reviewed</span>' : '<span class="chip">not checked further</span>'}</p>
      <p class="small">Additional Moon squares this candidate matches: ${r.N_ids.join(", ")}.</p>
      ${checked ? `<details><summary>What the checks found</summary>
        <p>${esc(c.satellite_visual_check)}</p>
        <p>Literature: no study naming this exact location was found; the wider region has documented Mars-analogue work (Ibn Battuta Centre sites in the
          Atlas/Anti-Atlas, Kereszturi et al., <em>Astrobiology</em> 2018; Tindouf Basin soil analogue,
          <a href="https://research-portal.st-andrews.ac.uk/en/publications/evaluation-of-the-tindouf-basin-region-in-southern-morocco-as-an-/">Oberlin, Claire &amp; Kounaves 2018</a>).
          This is not a discovery; more than 50 km from a known point does not mean unstudied.</p>
        <p>Vegetation screen: mean index (NDVI) ${c.candidate.ndvi_mean4} against a 0.15 cut-off (close to it). The elevation data is a surface model, so trees and buildings are not removed.
          This does not establish a new engineering test opportunity. Not a ready test site.</p>

      </details>` : ""}</div>`; }).join("");
  $("#cand-table").innerHTML = `<div class="tablewrap"><table><thead><tr><th>Site</th><th>Lat, lon</th><th>Flag</th><th>Matches missed by smaller list</th><th>Additional matches beyond full list</th></tr></thead><tbody>${
    rows.map((r) => `<tr><td>${r.id}</td><td>${r.lat.toFixed(2)}, ${r.lon.toFixed(2)}</td><td>${esc(r.novelty)}</td><td>${r.covers_gap_union}</td><td>${r.N_beyond_K}${r.N_ids.length ? ` (${r.N_ids.join(", ")})` : ""}</td></tr>`).join("")}</tbody></table></div>
    <p class="small">${R.global.processed} land points sampled (from ${R.global.drawn} random draws, 56°S–60°N, vegetation index &lt; 0.15): ${R.global.novelty_counts["Unverified"] || 0} Unverified,
      ${R.global.novelty_counts["Possibly known"] || 0} Possibly known, ${R.global.novelty_counts["Known"] || 0} Known. These are early ground-shape comparisons, not field-test assessments.
      Smaller list: ${D.sets.union.label}, ${D.sets.union.gap} unmatched. Full list: ${D.sets.K.label}, ${D.sets.K.gap} unmatched.</p>`;
  const inc = R.nasa_sites.included, keyOf = (name) => Object.keys(inc).find((k) => k.replace(/_/g, " ") === name);
  $("#nasa").innerHTML = Object.entries(R.report_card.sites).map(([name, v]) => { const s = inc[keyOf(name)];
    const links = s.citation.split(" ; ").map((u, i) => `<a href="${esc(u.trim())}">source ${i + 1}</a>`).join(" · ");
    return `<div class="cardx"><p style="margin:0"><strong>${esc(title(name))}</strong></p><div class="big">${v.moon_patches_covered} <span class="small">of ${v.denominator}</span></div>
      <p class="small">Moon squares matched by this sampled test-site window. This is not a rating of the whole site.</p><p>${esc(s.activity)}.</p><p class="small">${links}${name.startsWith("moses") ? " · coordinates approximate" : ""}</p></div>`; }).join("");
  $("#nasa-ex").innerHTML = `<ul>${Object.entries(R.nasa_sites.excluded).map(([k, v]) => `<li><strong>${esc(title(k.replace(/_/g, " ")))}</strong>: ${esc(v)}</li>`).join("")}</ul>
    <p class="small">${esc(R.report_card.note)}</p>`;
  $("#res-foot").textContent = `All results: ground-shape fingerprint, look-alike if d < ${D.T.toFixed(3)}; denominator ${D.sets.K.denominator} Moon patches; early result. Patch counts are not area fractions of the lunar south pole.`;
}

/* ---------- how we tested ---------- */
function tested() {
  const g2 = R.gate2, v1 = R.v1, g = R.g3v, ms = R.masked_slopes, st = g.step2_transparency_only, s = R.sensitivity.points, pct = (x) => f1(x * 100);
  $("#test-summary").innerHTML = `<p><strong>Failed:</strong> find a known rover test site from Mars dunes.</p>
    <p><strong>Failed:</strong> reliably retrieve other dune fields.</p><p><strong>Could not decide:</strong> beat a simple slope method.</p>`;
  $("#score").innerHTML = `
    <div class="cardx"><p><span class="pill failed">Failed</span></p><h3>Could Mars dunes find a known test site?</h3>
      <p>Starting from Mars sand dunes, the fingerprint did not rank Dumont Dunes (a NASA rover test site) in the top 10%: it came ${g2.dumont_rank_A} of ${g2.n_candidates}.</p>
      <details><summary>Details</summary><p>Pass/fail rule written before running: from a Bagnold dune patch in Gale crater (Mars), would Dumont Dunes, where NASA tested a Curiosity mobility stand-in
        in 2012, rank in the top 10% of ${g2.n_candidates} Mojave candidates? Rank ${g2.dumont_rank_A} under the primary metric (${g2.dumont_rank_secondary} secondary,
        ${g2.dumont_rank_B} with an image-embedding method). Measured on sand-only pixels, Dumont's median slope angle is about 3–5× higher than the Bagnold measurements
        (${ms.dumont_2m_median}° vs ${ms.bagnold_2m_median_min}–${ms.bagnold_2m_median_max}° at 2 m, ${ms.n_bagnold_boxes} boxes).</p></details></div>
    <div class="cardx"><p><span class="pill failed">Failed</span></p><h3>Could dune fields find each other?</h3>
      <p>Known Earth dune patches did not reliably retrieve each other (median rank ${v1.median_A}; ${v1.threshold} needed).</p>
      <details><summary>Details</summary><p>Retrieval test with its pass/fail rule written before running across Dumont, Kelso, Mesquite Flat and Eureka dunes: median rank of the other dune patches
        ${v1.median_A} (threshold ${v1.threshold} of ${v1.list_length}); ${v1.median_B} with the image-embedding method. Dune patches with large slip faces did find
        each other; smaller ridged dunes did not.</p></details></div>
    <div class="cardx"><p><span class="pill inconclusive">Inconclusive</span></p><h3>Did the fingerprint beat simple slope?</h3>
      <p id="g3v-line">Random picks had a median coverage of 100% in all 8 groups. The test could not tell the methods apart.</p>
      <details><summary>Details</summary>
        <p>Question: do sites picked with the full 30 m fingerprint cover more of the targets' metre-scale slope conditions than a simple slope-only method?
          Design: 8 new target groups × 3 windows (1.92 km) outside the earlier study box; ${g.n_windows} candidate windows grouped into ${g.n_sites} sites;
          up to 3 sites per method; 200 random combinations; scoring with 2 m lidar slopes.</p>
        <div class="tablewrap"><table><caption class="small">Metre-scale slope-condition coverage of each group's targets (%)</caption>
          <thead><tr><th>Group</th><th>Fingerprint</th><th>Slope only</th><th>Random median</th><th>Random 95th</th></tr></thead>
          <tbody>${g.groups.map((r) => `<tr><td>g${r.group}</td><td>${pct(r.A)}</td><td>${pct(r.B)}</td><td>${pct(r.random_median)}</td><td>${pct(r.random_p95)}</td></tr>`).join("")}</tbody></table></div>
        <p>The test could not decide: random 3-site picks reached a median of at least 95% in ${g.step1.n_groups_random_median_ge_95} of 8 groups. Why: ${esc(g.ceiling_explanation)}.</p>
        <p class="small">Published for transparency, not used to judge the methods: fingerprint above slope-only in ${st.A_beats_B_groups}/8 groups; median difference
          ${st.median_paired_A_minus_B_points} points; groups more than 10 points below: ${st.groups_A_worse_than_B_by_gt_10_points}; above random 95th:
          fingerprint ${st.A_above_random_p95_groups}/8, slope-only ${st.B_above_random_p95_groups}/8.</p>
        <figure class="chart"><img src="img/g3v_groups.png" alt="Bar chart of coverage per group for the fingerprint method, the slope-only method and the random reference" loading="lazy"></figure>
      </details></div>`;
  $("#sens").innerHTML = `<p>The unmatched count changes with the cut-off (original list of 29 USGS sites): ${s["50"].gap_n}/145 at the 50th percentile (T = ${s["50"].T}),
      ${s["90"].gap_n}/145 at the registered 90th (T = ${s["90"].T}), ${s["99"].gap_n}/145 at the 99th (T = ${s["99"].T}).</p>
    <figure class="chart"><img src="img/gap_threshold_sensitivity.png" alt="Line chart: share of the 145 Moon patches without a match against the threshold percentile, falling from about 87% to about 47%" loading="lazy"></figure>
    <p>Data-source change: the OpenTopography key reached its limit of 50 requests per day; before any affected result existed we registered a switch to the identical
      Copernicus GLO-30 files on AWS Open Data (at most 1.1 mm difference at Dumont).</p>`;
}

/* ---------- method ---------- */
function method() {
  $("#method-body").innerHTML = `
    <details class="disc"><summary>How we turn ground shape into numbers</summary><div class="inner">
      <p>For each 1.92 km window on a 30 m grid we measure how steep the ground is and how bumpy it is, at five scales (30, 60, 120, 240 and 480 m). We measure typical slope, its 90th percentile and its spread. Bumpiness is measured at 60–480 m after removing a tilted plane. We scale the 19 numbers using a fixed pool of Moon and Earth windows; two windows count as look-alikes when their distance d is below our fixed cut-off: ${D.T.toFixed(3)}.
        Gravity, soil, rocks below 30 m and lighting are not part of it.</p>
      <p class="small">The 19 features: ${D.feature_names.map(featLabel).join("; ")}.</p></div></details>
    <details class="disc"><summary>Data (NASA, ESA partner data, USGS)</summary><div class="inner"><ul>
      <li><strong>NASA:</strong> LRO LOLA <a href="https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/">LDEM_80S_20M</a> (Moon terrain);
        MRO HiRISE DTM DTEEC_040770_1755_039280_1755_U01 (<a href="https://hirise-pds.lpl.arizona.edu/PDS/">HiRISE PDS</a>, Mars dune test);
        MODIS MOD13C2 vegetation index (<a href="https://doi.org/10.5067/MODIS/MOD13C2.061">doi</a>, screening the global sample).</li>
      <li><strong>ESA partner data:</strong> <a href="https://registry.opendata.aws/copernicus-dem/">Copernicus GLO-30 DEM</a> (Earth windows at 30 m; via OpenTopography and AWS Open Data).</li>
      <li><strong>USGS:</strong> <a href="https://www.usgs.gov/3d-elevation-program">3DEP</a> 1 m lidar (Mojave tests); Known Terrestrial Analog Sites for Planetary Science,
        Hunter (2020), <a href="https://doi.org/10.5066/P9J72921">doi:10.5066/P9J72921</a>.</li></ul></div></details>
    <details class="disc"><summary>Prior work</summary><div class="inner"><ul>
      <li><a href="https://nhsjs.com/2026/finding-earths-best-testbeds-for-moon-and-mars-rovers-a-quantitative-terrain-comparison/">Sanganeria (2026)</a> ranks Earth sites by image
        texture in grayscale imagery. We compare elevation-derived slope and roughness at several scales instead, and report where no Earth match is found.</li>
      <li><a href="https://meetingorganizer.copernicus.org/EGU2013/EGU2013-11983.pdf">EGU2013-11983</a> analyses multi-scale elevation roughness of Mars landforms and their analogues.
        We apply a related idea to the lunar south pole against Earth analog and NASA test sites, with pass/fail rules written before each test.</li>
      <li><a href="https://ntrs.nasa.gov/citations/20000105009">NASA NTRS 20000105009</a>: cited, not summarised (we could not open the record).</li></ul></div></details>
    <details class="disc"><summary>AI assistance</summary><div class="inner">
      <p>Ron chose the challenge framing and direction. AI assistance: Claude (planning discussion and critique, drafting), Claude Code (research lookups and code),
        OpenAI Codex (plan review, layout and narrative edits, demo production, consistency checks). New and edited code identifies AI assistance. Ron reviews final text before submission.</p></div></details>`;
  $("#limits").innerHTML = [
    "The fingerprint-vs-slope test could not decide: many sampled sites already contained nearly every slope group.",
    "The unmatched count depends strongly on our cut-off. A look-alike is a result of this rule, not a natural category.",
    "The Earth elevation data is a surface model (trees and buildings included); Moon heights are quantised to 0.5 m and may be smoothed between laser tracks.",
    "Moses Lake coordinates are approximate; the USGS analog layer has label issues (Amboy listed as an impact crater; an Icelandic volcanic site listed as \"Ritland\").",
    "Patch counts are not area fractions of the lunar south pole.",
    "Earth comparisons do not reproduce gravity, vacuum, atmosphere or radiation, and nothing here tests vehicles, soil or hardware."
  ].map((t) => `<li>${esc(t)}</li>`).join("");
}

function bind() {
  document.querySelectorAll('input[name="set"]').forEach((r) => r.addEventListener("change", () => { state.set = r.value; drawMarkers(); drawPanel(false); }));
  $("#historical").addEventListener("change", (e) => {
    state.historical = e.target.checked;
    document.querySelectorAll('input[name="set"]').forEach((r) => (r.disabled = state.historical));
    drawMarkers(); drawPanel(false);
  });
}

Promise.all([fetch("data/display.json").then((r) => r.json()), fetch("data/results_summary.json").then((r) => r.json())])
  .then(([d, r]) => {
    D = d; R = r;
    const q = new URLSearchParams(location.search);
    state.patch = q.get("patch") || D.showcase.patch;
    state.sel = q.get("earth") || (state.patch === D.showcase.patch ? D.showcase.candidate : null);
    example(); bind(); drawMarkers(); drawPanel(false); results(); tested(); method();
    if (q.has("patch") || location.hash === "#explore") {
      $("#explorer-details").open = true;
      $("#explore").scrollIntoView({block: "start", behavior: "instant"});
    }
  })
  .catch((e) => { $("#panel").innerHTML = `<p>Could not load data: ${esc(e.message)}</p>`; console.error(e); });
