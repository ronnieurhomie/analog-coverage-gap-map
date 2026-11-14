# Portions of this file were generated with AI assistance (Claude Code, Anthropic) and reviewed by the author.
"""Verify Earthdata Login: netrc login, a CMR search, and an authenticated HEAD on one data file."""
import earthaccess

auth = earthaccess.login(strategy="netrc")
print("authenticated:", bool(auth and auth.authenticated))
res = earthaccess.search_data(short_name="NASADEM_HGT", bounding_box=(-116.3, 35.6, -116.2, 35.7), count=1)
print("NASADEM granules found:", len(res))
if res:
    url = res[0].data_links()[0]
    s = earthaccess.get_requests_https_session()
    r = s.head(url, allow_redirects=True, timeout=60)
    print("granule:", res[0]["umm"]["GranuleUR"], "| HEAD status:", r.status_code, "| bytes:", r.headers.get("Content-Length"))
