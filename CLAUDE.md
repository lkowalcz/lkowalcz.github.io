# lkowalcz.github.io

Personal website of Luke (Lucas) Kowalczyk. Plain static HTML — no build step, no framework, no Jekyll.

## Hosting setup

- **GitHub Pages** user site: published from the `main` branch, root directory, of `lkowalcz/lkowalcz.github.io`. Every push to `main` deploys automatically — there is no build/deploy CI to maintain. The only workflow (`.github/workflows/update-iex-volume.yml`) is a monthly data refresh, not part of deployment.
- **Custom domain:** `lukekowalczyk.com` (note: Luke, not Lucas), set via the `CNAME` file in the repo root. Do not delete or rename `CNAME` — that disconnects the domain. HTTPS is enforced in the GitHub Pages settings.
- **DNS / CDN:** the domain's DNS is managed by **Cloudflare**, which proxies traffic in front of GitHub Pages (the domain resolves to Cloudflare IPs, not GitHub's). Cloudflare's "Automatic HTTPS Rewrites" is active, and responses are cached briefly — a deployed change may take a few minutes to appear.
- **`.nojekyll`** (empty file) tells GitHub Pages to serve the files as-is instead of running the legacy Jekyll pipeline. Keep it.

## Site structure

- `index.html` — the entire site: one page with About / Research / Contact sections, toggled by a small vanilla-JS script at the end of `<body>` (no dependencies). Sections and photos are `.collapsible` divs; toggling adds/removes the `.collapsed` class, and a CSS `grid-template-rows` transition animates the slide. Clicking the photo swaps between two pictures (`images/me.jpg`, `images/pic2.jpg`).
- `stylesheet.css` — all styling, including the `.collapsible` animation, link-styled `<button>`s (`.linklike`), and a ≤600px media query for phones.
- **IEX volume chart** in the About section: vanilla JS at the end of `index.html` fetches `data/iex-volume.json` (monthly average daily matched volume since Jan 2014, same series as the chart on iextrading.com/stats) and draws an inline SVG line chart with a hover tooltip. If the fetch fails (e.g. opening the page via `file://`), the whole `<figure>` stays hidden. `scripts/update-iex-volume.py` (stdlib-only) regenerates the JSON — values through Jul 2021 are copied from IEX's own hardcoded JS, later months come one-per-request from `POST https://iextrading.com/api/stats/monthly` (that API has no CORS headers, which is why the data is snapshotted into the repo instead of fetched live). `.github/workflows/update-iex-volume.yml` runs the script on the 3rd of each month and commits if changed.
- `favicon.svg` — "LK" monogram favicon.
- Email addresses in `index.html` are plain `mailto:` links in the Contact section. There is deliberately no PGP key on the site — for encrypted contact, Luke prefers people email first and then move to Signal.

## Verifying a deploy

- Build status: `gh api repos/lkowalcz/lkowalcz.github.io/pages/builds/latest`
- Live site: `https://lukekowalczyk.com` (allow for Cloudflare cache, `max-age=600`)
