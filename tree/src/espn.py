"""ESPN public JSON helper: one fetch, cached on disk, fail-soft (returns cached copy or None, never raises)."""
import json, os, time, urllib.request
BASE = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/"
UA = {"User-Agent": "Mozilla/5.0 (KickTip data refresh; contact via kicktipmedia.com)"}
LOG = []

def fetch(url, cache_path=None, max_age=None, tries=3, timeout=30):
    """Return parsed JSON. If cache_path exists and is younger than max_age seconds (or max_age is None), use it.
    On network failure fall back to a stale cache copy; return None if neither exists."""
    if cache_path and os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if max_age is None or age < max_age:
            return json.load(open(cache_path))
    err = None
    for _ in range(tries):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout))
            if cache_path:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                tmp = cache_path + ".tmp"; json.dump(d, open(tmp, "w")); os.replace(tmp, cache_path)
            return d
        except Exception as e:  # fail soft
            err = e; time.sleep(1)
    LOG.append(f"FETCH FAILED {url}: {err}")
    if cache_path and os.path.exists(cache_path):
        LOG.append(f"  using stale cache {cache_path}")
        return json.load(open(cache_path))
    return None
