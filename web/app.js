// Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
// Display only: every number comes from data/display.json or data/results_summary.json (built from results/ by scripts/).
"use strict";

const RHO = 182100;                       // half-width of the hillshade in metres (data/lola_84S_hillshade.json)
const CANT_SEE = ["gravity (Earth 1 g, Moon 0.17 g)", "vacuum", "regolith mechanics", "illumination and thermal environment",
  "radiation", "rocks smaller than the 30 m DEM grid"];
let D, R, state = { set: "union", historical: false, patch: null, sel: null };

const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}) => Object.assign(document.createElement(tag), attrs);
const f1 = (x) => (Math.round(x * 10) / 10).toFixed(1);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const nice = (s) => String(s).replace(/^Mojave grid_r(\d)_c(\d)$/, "Gate 2 grid r$1 c$2").replace(/^Mojave dumont$/, "Dumont Dunes (Gate 2 grid window)")
  .replace(/^Mojave avawatz_negctrl$/, "Avawatz Mts (Gate 2 grid window)");
const title = (s) => String(s).replace(/\b\w/g, (c) => c.toUpperCase());

function featLabel(n) {
  const m = n.match(/^(slope|roughness)_(median|p90|iqr)_(\d+)m$/);
  const stat = { median: "median", p90: "90th-percentile", iqr: "interquartile range of" }[m[2]];
  return m[1] === "slope" ? `${stat} slope at ${m[3]} m` : `median roughness at ${m[3]} m`;
}
const unit = (n) => (n.startsWith("slope") ? "°" : " m");
const fval = (n, v) => (n.startsWith("slope") ? f1(v) : (Math.round(v * 100) / 100).toFixed(2)) + unit(n);

function activeKey() { return state.historical ? "historical" : state.set; }

function legendText() {
  const k = activeKey(), s = D.sets[k];
  const method = k === "historical" ? "fingerprint A, z-distance < T = 2.317 (Gate 3a)" : `fingerprint A, z-distance < T = ${D.T.toFixed(3)}`;
  return `<strong>Covered ${s.covered} / gap ${s.gap}</strong> of ${s.denominator} Moon patches · comparison set: ${esc(s.label)} · ` +
    `method: ${method} · nature: ${esc(s.nature)}.`;
}

function drawMarkers() {
  const map = $("#map");
  map.querySelectorAll(".pt").forEach((b) => b.remove());
  const k = activeKey();
  D.patches.forEach((p) => {
    const cov = p.status[k];
    const b = el("button", { className: "pt " + (cov ? "covered" : "gap"), type: "button" });
    b.style.left = ((p.x + RHO) / (2 * RHO) * 100) + "%";
    b.style.top = ((RHO - p.y) / (2 * RHO) * 100) + "%";
    b.setAttribute("aria-label", `Patch ${p.id}, ${p.lat.toFixed(2)}° latitude, ${p.lon.toFixed(1)}° longitude, ${cov ? "covered" : "gap"}`);
    b.setAttribute("aria-pressed", state.patch === p.id ? "true" : "false");
    b.addEventListener("click", () => { state.patch = p.id; state.sel = null; drawMarkers(); drawPanel(true); });
    map.appendChild(b);
  });
  $("#legend").innerHTML = legendText();
}

// selectable Earth windows for a patch: 5 neighbours from the pool, then global candidates within T
function items(p) {
  const nb = p.neighbours.map((n) => ({ id: n.id, name: nice(n.name), tag: n.set, d: n.distance, below: n.below_T }));
  const gc = (p.candidates || []).map((c) => ({ id: c.id, name: D.earth_names[c.id].name, tag: "global candidate (exploratory)" +
    (c.beyond_K ? "; gap under K" : ""), d: c.distance, below: c.below_T }));
  return { nb, gc, all: nb.concat(gc) };
}

function card(moonId, it) {
  const names = D.feature_names, a = D.features[moonId], b = D.features[it.id], sd = D.feature_sd;
  const z = names.map((n, i) => ({ n, a: a[i], b: b[i], dz: (a[i] - b[i]) / sd[i] }));
  const sim = z.filter((x) => Math.abs(x.dz) <= 1);
  const diff = [...z].sort((x, y) => Math.abs(y.dz) - Math.abs(x.dz)).slice(0, 3).filter((x) => Math.abs(x.dz) > 1);
  const i90 = names.indexOf("slope_p90_30m");
  const reach = b[i90] >= a[i90];
  return `<div class="card"><h4>Analog card (template, numbers only)</h4>
    <p class="overall"><strong>Overall: d = ${it.d.toFixed(2)}</strong> — ${it.below ? "within T (geometric neighbour)" : "not within T (nearest shown for comparison only)"}</p>
    <h4>Closest features <span class="note">(within one pooled SD)</span></h4>
    <ul>${sim.length ? sim.map((x) => `<li>${featLabel(x.n)}: Moon ${fval(x.n, x.a)}, Earth ${fval(x.n, x.b)}</li>`).join("") : "<li>none of the 19 features</li>"}</ul>
    <h4>Different <span class="note">(largest differences)</span></h4>
    <ul>${diff.length ? diff.map((x) => `<li>${featLabel(x.n)}: Moon ${fval(x.n, x.a)} vs Earth ${fval(x.n, x.b)} (${f1(Math.abs(x.dz))} pooled SD ${x.dz > 0 ? "higher" : "lower"} on the Moon)</li>`).join("") : "<li>no feature differs by more than one pooled SD</li>"}</ul>
    <h4>Can't see</h4><ul>${CANT_SEE.map((c) => `<li>${c}</li>`).join("")}</ul>
    <h4>Could test here</h4><ul><li>Slope range: this Earth window's 90th-percentile slope at 30 m is ${fval(names[i90], b[i90])} against the Moon patch's ${fval(names[i90], a[i90])}; ${reach ? "it reaches the Moon patch's range" : "it does not reach the Moon patch's range"}. Geometry only, untested for vehicles.</li></ul></div>`;
}

function drawPanel(focus) {
  const p = D.patches.find((x) => x.id === state.patch); if (!p) return;
  const k = activeKey(), s = D.sets[k], cov = p.status[k];
  const fn = D.feature_names, f = D.features[p.id], idx = (n) => fn.indexOf(n);
  const its = items(p);
  const it = its.all.find((x) => x.id === state.sel) || its.all[0];
  state.sel = it.id;
  const btn = (x) => `<li><button type="button" data-id="${esc(x.id)}" aria-pressed="${x.id === it.id}">
      ${esc(x.name)} <span class="tag">${esc(x.tag)}</span> d = ${x.d.toFixed(2)} ${x.below ? "(d &lt; T)" : "(d ≥ T)"}</button></li>`;
  const panel = $("#panel");
  panel.innerHTML = `<h3>Moon patch ${p.id}</h3>
    <dl class="kv"><dt>Centre</dt><dd>${p.lat.toFixed(3)}°, ${p.lon.toFixed(2)}° (polar stereographic x ${(p.x / 1000).toFixed(1)} km, y ${(p.y / 1000).toFixed(1)} km)</dd>
      <dt>Median slope 30 m</dt><dd>${fval("slope", f[idx("slope_median_30m")])}</dd>
      <dt>90th-pct slope 30 m</dt><dd>${fval("slope", f[idx("slope_p90_30m")])}</dd>
      <dt>Median slope 480 m</dt><dd>${fval("slope", f[idx("slope_median_480m")])}</dd>
      <dt>Status</dt><dd><span class="status ${cov ? "covered" : "gap"}">${cov ? "covered" : "gap"}</span> against ${esc(s.label)} (${esc(s.nature)})</dd></dl>
    <h4>5 nearest windows in the neighbour pool <span class="note">(z-distance d; T = ${D.T.toFixed(3)})</span></h4>
    <p class="note">${esc(D.neighbour_pool)}</p>
    <ul class="nb">${its.nb.map(btn).join("")}</ul>
    ${its.gc.length ? `<h4>Global candidates within T <span class="note">(exploratory)</span></h4><ul class="nb">${its.gc.map(btn).join("")}</ul>` : ""}
    <div class="pair">
      <figure><img src="img/moon/${p.id}.png" alt="Shaded relief of Moon patch ${p.id}, 1.92 km square" width="192" height="192">
        <div class="scalebar"></div><span>500 m</span><figcaption>Moon ${p.id}</figcaption></figure>
      <figure><img src="img/earth/${esc(it.id)}.png" alt="Shaded relief of Earth window ${esc(it.name)}, 1.92 km square" width="192" height="192">
        <div class="scalebar"></div><span>500 m</span><figcaption>Earth: ${esc(it.name)}</figcaption></figure>
    </div>
    <p class="note">Same physical extent (1.92 km × 1.92 km, 30 m grid) and same sun (azimuth 315°, altitude 30°).</p>
    ${card(p.id, it)}`;
  panel.querySelectorAll(".nb button").forEach((b) => b.addEventListener("click", () => { state.sel = b.dataset.id; drawPanel(false); }));
  if (focus) panel.focus({ preventScroll: window.innerWidth > 820 });
}

function candidate() {
  const c = R.candidate, g = R.global, cc = c.coverage_contribution, nov = g.novelty_counts, inc = D.increment, K = D.sets.K;
  const g94 = inc.g00094;
  const rows = inc.candidates.map((r) => `<tr><td>${esc(r.id)}</td><td>${r.lat.toFixed(2)}, ${r.lon.toFixed(2)}</td><td>${esc(r.novelty)}</td>
    <td>${r.covers_gap_union}</td><td>${r.N_beyond_K}${r.N_ids.length ? ` (${r.N_ids.join(", ")})` : ""}</td></tr>`).join("");
  $("#cand-body").innerHTML = `
    <p>Global sample point <strong>${c.candidate.id}</strong> at ${c.candidate.lat.toFixed(3)}°N, ${Math.abs(c.candidate.lon).toFixed(3)}°W
      (southern Morocco, inferred from coordinates only). Data: Copernicus GLO-30 DEM (surface model), 1.92 km window at 30 m.</p>
    <p><strong>Against the current comparison set</strong> (USGS-29 ∪ 3 NASA test sites; fingerprint A, T = 2.317; denominator 145; exploratory):
      within the threshold for ${cc.n_gap_patches_covered} of the ${cc.n_current_gap_patches} gap patches.</p>
    <p id="cand-net"><strong>Beyond the fuller known set (all usable USGS analog sites + 3 NASA test sites), this candidate still gives ${g94.N} Moon targets a geometric neighbour under the exploratory threshold</strong>
      (${g94.still_gap_under_K.join(", ")}; the fuller set K covers ${K.covered} and leaves ${K.gap} of 145 as gaps; post-hoc set operation, exploratory).</p>
    <p>This is not a filled engineering-test gap and not ready for field testing. <span class="badge">Unverified</span> does not mean newly found:
      the wider region has documented Mars-analogue work, and being more than 50 km from a known point does not mean unstudied.</p>
    <figure class="wide"><img src="img/candidate_case_web.png" alt="Shaded relief of the Earth window g00094 next to two Moon patches it is geometrically close to, all 1.92 km at the same sun angle" loading="lazy">
      <figcaption>Same-scale hillshades (1.92 km, 30 m grid, sun azimuth 315°, altitude 30°): g00094 and two Moon patches within its threshold.</figcaption></figure>
    <ul>
      <li>Nearest known site in our lists: ${esc(c.novelty.nearest_known)}, ${c.novelty.nearest_known_km} km away.</li>
      <li>Literature check (web search, 2026-11-15): no study naming this exact location was found; the wider region has documented
        Mars-analogue work: the Ibn Battuta Centre analogue sites in the Atlas/Anti-Atlas (Kereszturi et al., <em>Astrobiology</em>, 2018)
        and the Tindouf Basin soil-geochemistry analogue (<a href="https://research-portal.st-andrews.ac.uk/en/publications/evaluation-of-the-tindouf-basin-region-in-southern-morocco-as-an-/">Oberlin, Claire &amp; Kounaves, 2018</a>).</li>
      <li>${esc(c.satellite_visual_check)}</li>
      <li>Vegetation screen: mean NDVI ${c.candidate.ndvi_mean4} against a cut-off of 0.15 (close to the cut-off). The DEM is a surface model,
        so vegetation or structures are not removed.</li>
      <li>Untested: ${c.untested_conditions.map(esc).join("; ")}.</li>
    </ul>
    <h3>All global candidates</h3>
    <p>${g.processed} land points processed (from ${g.drawn} random draws, 56°S–60°N, NDVI &lt; 0.15): ${nov["Unverified"] || 0} Unverified,
      ${nov["Possibly known"] || 0} Possibly known, ${nov["Known"] || 0} Known. ${g.n_covering_any_gap} of them are within the threshold for at least one current gap patch.
      All are geometric neighbours, exploratory.</p>
    <div class="tablewrap"><table><caption class="note">Gap patches within T: fingerprint A, T = 2.317, denominator 145, exploratory.
      "Current gaps" = gaps for USGS-29 ∪ 3 NASA test sites (85); "beyond K" = still gaps for all usable USGS sites ∪ 3 NASA test sites (60).</caption>
      <thead><tr><th>Candidate</th><th>Lat, lon</th><th>Flag</th><th>Current gaps within T</th><th>Beyond K</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function reportCard() {
  const rc = R.report_card, inc = R.nasa_sites.included, exc = R.nasa_sites.excluded;
  const keyOf = (name) => Object.keys(inc).find((k) => k.replace(/_/g, " ") === name);
  const rows = Object.entries(rc.sites).map(([name, v]) => {
    const s = inc[keyOf(name)];
    const links = s.citation.split(" ; ").map((u, i) => `<a href="${esc(u.trim())}">source ${i + 1}</a>`).join(", ");
    return `<tr><td>${esc(title(name))}</td><td>${v.moon_patches_covered} / ${v.denominator} covered</td><td>${v.slope_bins_provided_30m.map(esc).join(" ")}</td>
      <td>${esc(s.activity)} (${links})${name.startsWith("moses") ? "<br><em>Coordinates approximate (recreation listings).</em>" : ""}</td></tr>`;
  }).join("");
  $("#rc-body").innerHTML = `<p class="note">Fingerprint A, T = 2.317; denominator 145 Moon patches; current method, exploratory. ${esc(rc.note)}</p>
    <div class="tablewrap"><table><thead><tr><th>Site</th><th>Moon patches</th><th>30 m slope bins present (°)</th><th>NASA/JPL activity</th></tr></thead>
    <tbody>${rows}</tbody></table></div>
    <p class="note">Left out: ${Object.entries(exc).map(([k, v]) => `${esc(title(k.replace(/_/g, " ")))}: ${esc(v)}`).join(" · ")}.</p>`;
}

function tested() {
  const g2 = R.gate2, v1 = R.v1, g = R.g3v, s = R.sensitivity.points, ms = R.masked_slopes, st = g.step2_transparency_only;
  const pct = (x) => f1(x * 100);
  $("#tested-body").innerHTML = `
    <h3>Gate 2 (pre-registered, failed)</h3>
    <p>Starting from a Bagnold dune patch in Gale crater (Mars), would Dumont Dunes (where NASA tested a Curiosity mobility stand-in in 2012)
      rank in the top 10% of ${g2.n_candidates} Mojave candidates? It ranked ${g2.dumont_rank_A} under the primary metric
      (${g2.dumont_rank_secondary} secondary, ${g2.dumont_rank_B} with an image-embedding method). Failed.
      Measured on sand-only pixels, Dumont's median slope angle is about 3–5× higher than the Bagnold boxes
      (${ms.dumont_2m_median}° vs ${ms.bagnold_2m_median_min}–${ms.bagnold_2m_median_max}° at 2 m, ${ms.n_bagnold_boxes} boxes).</p>
    <h3>V1 (pre-registered, failed)</h3>
    <p>Do known Earth dune patches retrieve each other? Median rank of the other dune patches: ${v1.median_A} (threshold ${v1.threshold} of ${v1.list_length});
      ${v1.median_B} with the image-embedding method. Failed. Dune patches with large slip faces did find each other; smaller ridged dunes did not.</p>
    <h3 id="g3v-h">G3v acceptance test (pre-registered): ${esc(g.branch)}</h3>
    <p><strong>Question:</strong> do sites picked with the full 30 m fingerprint cover more of the targets' metre-scale slope conditions than a simple
      slope-only method? <strong>Design:</strong> 8 new target groups × 3 windows (1.92 km) outside the earlier study box; ${g.n_windows} candidate windows
      grouped into ${g.n_sites} sites; up to 3 sites per method; random reference of 200 combinations; scoring with 2 m lidar slopes.</p>
    <div class="tablewrap"><table><caption class="note">Metre-scale slope-condition coverage of each group's targets (%)</caption>
      <thead><tr><th>Group</th><th>A fingerprint</th><th>B slope only</th><th>Random median</th><th>Random 95th</th></tr></thead>
      <tbody>${g.groups.map((r) => `<tr><td>g${r.group}</td><td>${pct(r.A)}</td><td>${pct(r.B)}</td><td>${pct(r.random_median)}</td><td>${pct(r.random_p95)}</td></tr>`).join("")}</tbody></table></div>
    <p id="g3v-step1"><strong>Step 1 = ${esc(g.branch)}:</strong> random 3-site picks already reached a median of at least 95% in ${g.step1.n_groups_random_median_ge_95} of 8 groups,
      so the test could not tell the methods apart. Why: ${esc(g.ceiling_explanation)}.</p>
    <p class="note">Transparency only, not a verdict (Step 2 was not applied): A above B in ${st.A_beats_B_groups}/8 groups; median A − B ${st.median_paired_A_minus_B_points} points;
      groups with A more than 10 points below B: ${st.groups_A_worse_than_B_by_gt_10_points}; A above random 95th: ${st.A_above_random_p95_groups}/8; B above random 95th: ${st.B_above_random_p95_groups}/8.</p>
    <figure class="wide"><img src="img/g3v_groups.png" alt="Bar chart of G3v coverage per group for method A, method B and the random reference" loading="lazy"></figure>
    <h3>Threshold sensitivity (post-hoc)</h3>
    <p>With the historical USGS-29 set, the gap depends strongly on the threshold T: ${s["50"].gap_n}/145 gap at the 50th percentile (T = ${s["50"].T}),
      ${s["90"].gap_n}/145 at the registered 90th (T = ${s["90"].T}), ${s["99"].gap_n}/145 at the 99th (T = ${s["99"].T}).</p>
    <figure class="wide"><img src="img/gap_threshold_sensitivity.png" alt="Line chart: gap share of 145 Moon patches against threshold percentile, falling from about 87% to about 47%" loading="lazy"></figure>
    <h3>Data-source change</h3>
    <p>The OpenTopography key reached its limit of 50 requests per day. Before any affected result existed, we registered a switch to the identical
      Copernicus GLO-30 files on AWS Open Data (at most 1.1 mm difference at Dumont).</p>
    <h3>Limitations</h3>
    <ul><li>G3v cannot discriminate: with 1.92 km windows and a 5% bin rule, almost any site contains almost every slope bin.</li>
      <li>Moses Lake coordinates come from recreation listings; region reference points for the novelty flags are approximate; the candidate's country is inferred from coordinates.</li>
      <li>USGS analog layer label issues (Amboy listed as an impact crater; an Icelandic volcanic site listed as "Ritland").</li>
      <li>LOLA heights are quantised to 0.5 m and may be smoothed between laser tracks; Copernicus GLO-30 is a surface model.</li>
      <li>Patch counts are not area fractions of the lunar south pole. Earth comparisons do not reproduce gravity, vacuum, atmosphere or radiation.</li></ul>`;
}

function method() {
  $("#method-body").innerHTML = `
    <h3>The fingerprint in plain words</h3>
    <p>For each 1.92 km window on a 30 m grid we measure how steep the ground is and how bumpy it is, at five scales (30, 60, 120, 240 and 480 m):
      the median, 90th percentile and spread of slope, plus the roughness left after removing a tilted plane. Each of the 19 numbers is
      standardised with the mean and spread of a fixed pool of Moon and Earth windows, and two windows are geometric neighbours when their distance d is below T = ${D.T.toFixed(3)}.
      Gravity, soil, rocks below 30 m and lighting are not part of it.</p>
    <p class="note">Features: ${D.feature_names.map(featLabel).join("; ")}.</p>
    <h3>Data</h3>
    <ul><li>Moon: NASA LRO LOLA <a href="https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/">LDEM_80S_20M</a> (PDS Geosciences Node).</li>
      <li>Mars (Gates 1–2): MRO HiRISE DTM DTEEC_040770_1755_039280_1755_U01 (<a href="https://hirise-pds.lpl.arizona.edu/PDS/">HiRISE PDS</a>).</li>
      <li>Earth: <a href="https://registry.opendata.aws/copernicus-dem/">Copernicus GLO-30 DEM</a> (via OpenTopography and AWS Open Data);
        <a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a> 1 m lidar (Mojave tests); NASADEM (cross-check of the Gate 3 site windows,
        <a href="https://doi.org/10.5067/MEaSUREs/NASADEM/NASADEM_HGT.001">doi</a>); MODIS MOD13C2 NDVI (vegetation screen,
        <a href="https://doi.org/10.5067/MODIS/MOD13C2.061">doi</a>).</li>
      <li>Analog sites: USGS Known Terrestrial Analog Sites for Planetary Science, Hunter (2020), <a href="https://doi.org/10.5066/P9J72921">doi:10.5066/P9J72921</a>.</li></ul>
    <h3>Prior work and how this differs</h3>
    <ul><li><a href="https://nhsjs.com/2026/finding-earths-best-testbeds-for-moon-and-mars-rovers-a-quantitative-terrain-comparison/">Sanganeria (2026)</a> ranks Earth sites by image texture
        in grayscale imagery. We compare elevation-derived slope and roughness at several scales instead, and report where no Earth match is found.</li>
      <li><a href="https://meetingorganizer.copernicus.org/EGU2013/EGU2013-11983.pdf">EGU2013-11983</a> analyses multi-scale DEM roughness of Mars landforms and their analogues.
        We apply a related idea to the lunar south pole against Earth analog and NASA test sites, with pre-registered tests.</li>
      <li><a href="https://ntrs.nasa.gov/citations/20000105009">NASA NTRS 20000105009</a>: cited, not summarised (we could not open the record).</li></ul>
    <h3>AI assistance</h3>
    <p>Ron chose the challenge framing and direction. AI assistance: Claude (planning discussion and critique, drafting), Claude Code (research lookups and code),
      OpenAI Codex (plan review). Source files carry headers; Ron reviewed the work.</p>
    <p>Licence: MIT. Repository link: <span class="placeholder-link">[to be added]</span>.</p>`;
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
    D = d; R = r; bind(); drawMarkers(); candidate(); reportCard(); tested(); method();
    const params = new URLSearchParams(location.search);
    if (params.get("patch")) { state.patch = params.get("patch"); state.sel = params.get("earth"); drawMarkers(); drawPanel(false); }
  })
  .catch((e) => { $("#panel").innerHTML = `<p>Could not load data: ${esc(e.message)}</p>`; console.error(e); });
