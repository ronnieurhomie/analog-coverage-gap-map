# AI assistance: OpenAI Codex. Checks display consistency against the fact ledger and existing JSON.
"""Check changed flows locally, or pass the public URL. Does not run new science."""
import functools
import hashlib
import http.server
import json
import math
import re
import sys
import threading
from urllib.parse import urlsplit
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?(?![\w.])")


def values(v):
    if isinstance(v, dict):
        for x in v.values():
            yield from values(x)
    elif isinstance(v, list):
        for x in v:
            yield from values(x)
    elif isinstance(v, (float, int)) and not isinstance(v, bool):
        yield float(v)


def tokens(s):
    # URLs, product IDs and named patch IDs are identifiers, not measured quantities.
    s = re.sub(r"https?://\S+", "", s)
    return {abs(float(t.replace(',', ''))) for t in TOKEN.findall(s)}


def main():
    d = json.loads((ROOT / 'web/data/display.json').read_text())
    r = json.loads((ROOT / 'web/data/results_summary.json').read_text())
    ledger = (ROOT / 'docs/FACTS.md').read_text()
    facts = json.loads(re.search(r'```json\n(.*?)\n```', ledger, re.S).group(1))
    assert all(facts['checks'].values())
    assert facts['K_unmatched'] == d['sets']['K']['gap'] == 60
    assert facts['random_new_matches'] == d['clarity']['random_additional_count'] == 6
    assert facts['Mojave_new_matches'] == d['clarity']['mojave_additional_count'] == 5
    assert d['showcase']['patch'] == 'm014'
    assert all(sum(bool(p['status'][key]) for p in d['patches']) == s['covered'] for key, s in d['sets'].items())
    assert all(p['known_K']['below_T'] == p['status']['K'] for p in d['patches'])

    # Numeric-source whitelist plus semantic assertions below: swapping 60/85 is still caught.
    allowed = tokens(ledger)
    # Citation IDs, years and coordinates inside source strings are ledger-backed too.
    allowed.update(tokens(json.dumps([d, r])))
    for x in values([d, r, facts]):
        for digits in range(5):
            allowed.add(abs(round(x, digits)))
            allowed.add(abs(math.floor(x * 10 ** digits + 0.5) / 10 ** digits))
    for group in r['g3v']['groups']:
        for key in ['A', 'B', 'random_median', 'random_p95']:
            allowed.add(round(group[key] * 100, 1))

    submission = (ROOT / 'docs/SUBMISSION.md').read_text()
    summary = submission.split('## High-Level Project Summary\n', 1)[1].split('\n## ', 1)[0]
    assert 50 <= len(summary.split()) <= 200
    assert r'\n' not in submission, 'Literal escaped newlines in copy-ready submission'

    bad_words = []
    files = [ROOT / 'README.md', ROOT / 'docs/SUBMISSION.md'] + [
        p for p in (ROOT / 'web').rglob('*') if p.suffix in {'.html', '.js', '.css', '.json', '.vtt', '.txt'}]
    banned = re.compile(r"\b(?:validated|discovery|best site|proves|harder|dangerous)\b|can['’]t we test", re.I)
    for p in files:
        # Explicit negative statements preserve the scientific limitation; positive claims still fail.
        body = re.sub(r'not (?:a discovery|a validated site-selection system|a newly discovered or field-validated test site)', '', p.read_text(), flags=re.I)
        if banned.search(body):
            bad_words.append(str(p.relative_to(ROOT)))
    assert not bad_words, bad_words

    httpd = None
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *_):
                pass
        handler = functools.partial(QuietHandler, directory=str(ROOT / 'web'))
        httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 8771), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        url = 'http://127.0.0.1:8771/'
    local = httpd is not None
    shots = ROOT / 'docs/screenshots'
    shots.mkdir(parents=True, exist_ok=True)
    report = {'url': url, 'banned_word_mismatches': bad_words, 'widths': {}, 'numeric_mismatches': []}
    errors, failed, media_cancellations = [], [], []
    def request_failed(q):
        if urlsplit(q.url).path.endswith('/demo/demo.mp4') and q.failure == 'net::ERR_ABORTED':
            # Chromium may cancel its metadata preload, then issue a playback request.
            # Independently require HTTP 200, exact file hash, decoded metadata and playback below.
            media_cancellations.append({'url': q.url, 'reason': q.failure})
        else:
            failed.append({'url': q.url, 'reason': q.failure})
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for name, width, height in [('desktop', 1280, 720), ('mobile', 390, 844)]:
            ctx = browser.new_context(viewport={'width': width, 'height': height}, color_scheme='light')
            page = ctx.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.on('requestfailed', request_failed)
            page.on('response', lambda q: failed.append(f'{q.status} {q.url}') if q.status >= 400 else None)
            page.goto(url, wait_until='networkidle')
            page.wait_for_selector('#earth-choice')
            primary_text = page.locator('main').inner_text()
            primary_words = len(primary_text.split())
            assert page.locator('#map').is_visible()
            assert page.locator('#explorer-details').count() == 0
            map_box = page.locator('#map').bounding_box()
            assert map_box['y'] + map_box['height'] < height, (name, map_box)
            assert 'Choose Moon terrain' in page.locator('.hero').inner_text()
            assert page.locator('#earth-choice').input_value() == 'g00094'
            for figure in page.locator('#panel .pair figure').all():
                ratio=figure.locator('.scale i').bounding_box()['width']/figure.locator('img').bounding_box()['width']
                assert abs(ratio-500/1920) < 0.01, ratio
            assert page.locator('.pt').count() == facts['moon_count']
            assert page.locator('input[name="set"]:checked').input_value() == 'K'
            assert page.locator('.pt[aria-pressed="true"]').get_attribute('aria-label').startswith('Patch m014,')
            legend = page.locator('#legend').text_content()
            assert d['sets']['K']['label'] in legend and '85 matched, 60 no match' in legend
            assert d['sets']['K']['label'] in page.locator('#bars').inner_text()
            first_bar = page.locator('#bars .barrow').first.inner_text()
            assert '85 matched' in first_bar and '60 no match' in first_bar
            assert f"{d['showcase']['candidate_d']:.3f}" in page.locator('#trio').text_content()
            assert f"{d['showcase']['known_d']:.3f}" in page.locator('#trio').text_content()
            assert d['showcase']['known_name'] in page.locator('#earth-choice').text_content()
            assert '6 of the 60' in page.locator('#bars').inner_text()
            assert '5 of the 60' in page.locator('#other-bars').text_content()
            assert page.locator('#score .pill.failed').count() == 2
            assert page.locator('#score .pill.inconclusive').count() == 1
            overflow = page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            assert overflow == 0, (name, overflow)
            hero_bottom = page.locator('.hero').bounding_box()['y'] + page.locator('.hero').bounding_box()['height']
            if name == 'desktop':
                assert hero_bottom <= 720, hero_bottom
                metric_box=page.locator('.metric-table').bounding_box()
                assert metric_box['y']+metric_box['height'] <= height, metric_box
            if local:
                page.screenshot(path=str(shots / f'clarity_{name}_hero.png'))
                if name == 'desktop':
                    for sec in ['explore']:
                        page.locator('#' + sec).screenshot(path=str(shots / f'clarity_{sec}.png'))
            # Comparison settings change both legend and markers; K remains the default.
            page.locator('.settings > summary').click()
            for key in ['union', 'nasa', 'allusgs', 'K']:
                page.locator(f'input[name="set"][value="{key}"]').check()
                assert page.locator('.pt.covered').count() == d['sets'][key]['covered'], key
            page.locator('#historical').check()
            assert page.locator('.pt.covered').count() == d['sets']['historical']['covered']
            page.locator('#historical').uncheck()
            page.locator('.settings > summary').click()
            # Direct manipulation updates imagery, source measurements and verdict together.
            page.locator('#earth-choice').select_option(d['showcase']['known_id'])
            assert 'Outside the shape cut-off' in page.locator('#compare-status').inner_text()
            assert d['showcase']['known_id'] in page.locator('#panel .pair img').nth(1).get_attribute('src')
            assert page.locator('#earth-choice').evaluate('(e)=>e===document.activeElement')
            page.locator('#earth-choice').select_option('g00094')
            assert 'Within the shape cut-off' in page.locator('#compare-status').inner_text()
            assert 'g00094' in page.locator('#panel .pair img').nth(1).get_attribute('src')
            assert '14.3°' in page.locator('.metric-table').inner_text()
            first_covered = next(p for p in d['patches'] if p['status']['K'])
            page.locator(f'.pt[data-patch="{first_covered["id"]}"]').click()
            assert first_covered['id'] in page.locator('#panel .pair img').first.get_attribute('src')
            assert first_covered['id'] in page.locator('#selection-status').inner_text()
            assert 'Within the shape cut-off' in page.locator('#compare-status').inner_text()
            if name == 'mobile':
                page.wait_for_timeout(500)
                assert 0 <= page.locator('#panel').bounding_box()['y'] < 100
                if local: page.screenshot(path=str(shots / 'clarity_mobile_comparison.png'))
                page.locator('#back-to-map').click()
            page.locator('#reset-example').click()
            assert page.locator('#earth-choice').input_value() == 'g00094'
            selected=page.locator('.pt[aria-pressed="true"]')
            selected.focus()
            selected.press('ArrowRight')
            assert not page.locator('.pt[aria-pressed="true"]').get_attribute('aria-label').startswith('Patch m014,')
            assert page.locator('.pt[aria-pressed="true"]').evaluate('(e)=>e===document.activeElement')
            page.locator('#reset-example').click()
            page.emulate_media(reduced_motion='reduce')
            assert page.locator('#panel .pair').evaluate('(e)=>getComputedStyle(e).animationName') == 'none'
            page.emulate_media(reduced_motion='no-preference')
            disclosures = page.locator('details').count()
            for detail in page.locator('details').all():
                if not detail.evaluate('(e) => e.open'):
                    detail.locator('summary').first.click()
                assert detail.evaluate('(e) => e.open')
            body = page.locator('body').inner_text()
            mismatches = sorted(x for x in tokens(body) if not any(abs(x - y) < 0.000001 for y in allowed))
            report['numeric_mismatches'] += [{'width': width, 'value': x} for x in mismatches]
            if local and name == 'desktop':
                (shots / 'clarity_page_text.txt').write_text(body)
            report['widths'][name] = {'viewport': [width, height], 'markers': 145, 'default': 'K',
                                     'showcase': 'm014', 'overflow_px': overflow, 'hero_bottom_px': hero_bottom,
                                     'disclosures_opened': disclosures, 'comparison_switching': True,
                                     'set_totals_match': True, 'numeric_mismatches': mismatches,
                                     'primary_words': primary_words, 'map_visible_on_first_screen': True,
                                     'keyboard_selection': True, 'mobile_result_reveal': name == 'mobile',
                                     'reduced_motion': True}
            page.locator('img').evaluate_all("(imgs) => Promise.all(imgs.map(i => { i.loading = 'eager'; return i.decode(); }))")
            page.wait_for_load_state('networkidle')
            page.goto(url.rstrip('/') + '/?patch=m000#explore', wait_until='networkidle')
            page.wait_for_selector('#panel .pair')
            assert page.locator('.pt[aria-pressed="true"]').get_attribute('aria-label').startswith('Patch m000,')
            report['widths'][name]['existing_target_link_opens_map'] = True
            page.locator('img').evaluate_all("(imgs) => Promise.all(imgs.map(i => { i.loading = 'eager'; return i.decode(); }))")
            page.wait_for_load_state('networkidle')
            page.goto(url.rstrip('/') + '/demo/', wait_until='networkidle')
            page.wait_for_function("document.querySelector('video').readyState >= 1")
            video = page.locator('video')
            metadata = video.evaluate('(v) => ({duration:v.duration,width:v.videoWidth,height:v.videoHeight,tracks:v.textTracks.length})')
            assert 0 < metadata['duration'] <= 30
            assert metadata['width'] == 1920 and metadata['height'] == 1080 and metadata['tracks'] == 1
            video.evaluate('(v) => {v.muted=true; return v.play()}')
            page.wait_for_function("document.querySelector('video').currentTime > 0.2")
            response = ctx.request.get(url.rstrip('/') + '/demo/demo.mp4')
            assert response.status == 200 and 'video/mp4' in response.headers.get('content-type', '')
            same_file = hashlib.sha256(response.body()).digest() == hashlib.sha256((ROOT / 'web/demo/demo.mp4').read_bytes()).digest()
            assert same_file and video.evaluate('(v) => v.error === null')
            report['widths'][name]['demo'] = {**metadata, 'playback_advances': True, 'mp4_http': response.status,
                                            'matches_checked_file_sha256': same_file}
            ctx.close()
        browser.close()
    if httpd:
        httpd.shutdown()
    report['console_errors'] = errors
    report['failed_requests'] = failed
    report['media_metadata_request_cancellations'] = media_cancellations
    print(json.dumps(report, indent=2))
    suffix = 'local' if local else 'public'
    (ROOT / f'docs/clarity_check_{suffix}.json').write_text(json.dumps(report, indent=2))
    assert not errors and not failed and not report['numeric_mismatches'], report


if __name__ == '__main__':
    main()
