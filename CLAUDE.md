# lkowalcz.github.io

Personal website of Luke (Lucas) Kowalczyk. Plain static HTML — no build step, no framework, no Jekyll.

## Hosting setup

- **GitHub Pages** user site: published from the `main` branch, root directory, of `lkowalcz/lkowalcz.github.io`. Every push to `main` deploys automatically — there is no build/deploy CI to maintain. The only workflow (`.github/workflows/update-iex-notional.yml`) is a monthly data refresh, not part of deployment.
- **Custom domain:** `lukekowalczyk.com` (note: Luke, not Lucas), set via the `CNAME` file in the repo root. Do not delete or rename `CNAME` — that disconnects the domain. HTTPS is enforced in the GitHub Pages settings.
- **DNS / CDN:** the domain's DNS is managed by **Cloudflare**, which proxies traffic in front of GitHub Pages (the domain resolves to Cloudflare IPs, not GitHub's). Cloudflare's "Automatic HTTPS Rewrites" is active, and responses are cached briefly — a deployed change may take a few minutes to appear.
- **`.nojekyll`** (empty file) tells GitHub Pages to serve the files as-is instead of running the legacy Jekyll pipeline. Keep it.

## Site structure

- `index.html` — the entire site: one page with About / Publications / Contact sections, toggled by a small vanilla-JS script at the end of `<body>` (no dependencies). Sections and photos are `.collapsible` divs, and exactly one top-level panel is open at a time (a section, or else the current photo); `show(id)` adds/removes the `.collapsed` class, and a CSS `grid-template-rows` transition animates the slide. Clicking the photo swaps between two pictures (`images/me.jpg`, `images/pic2.jpg`).
- `stylesheet.css` — all styling; the palette lives in five custom properties on `:root` (`--ink`, `--muted`, `--rule`, `--link`, `--link-hover`). Includes the `.collapsible` animation, link-styled `<button>`s (`.linklike`), and fluid sizing (`clamp()`/`min()`/`max()`) for the name, menu, photo, and text column instead of a phone media query — laptop widths (≥1024px) render exactly as the old fixed sizes did. Collapsed sections also get the `inert` attribute (set in JS, so the noscript fallback still works) to keep hidden links out of the tab order.
- **IEX dollar-volume chart** in the About section: vanilla JS at the end of `index.html` fetches `data/iex-notional.json` (monthly average daily traded dollar value since Sep 2020) and draws an inline SVG line chart with a hover tooltip. If the fetch fails (e.g. opening the page via `file://`), the whole `<figure>` stays hidden. IEX's own public stats are share-denominated only, so dollars come from Cboe's market share pages: `scripts/update-iex-notional.py` (stdlib-only) scrapes the `mtd_data` blob embedded in `cboe.com/us/equities/market_share/market/all/<1st of next month>/` — that page reports the prior month's full average daily notional (validated: its Volume counterpart matches IEX's published share ADV exactly). Data is snapshotted into the repo because neither IEX nor Cboe serves CORS-enabled JSON. `.github/workflows/update-iex-notional.yml` runs the script on the 3rd of each month and commits if changed.
- `favicon.svg` — "LK" monogram favicon.
- Email addresses in `index.html` are plain `mailto:` links in the Contact section. There is deliberately no PGP key on the site — for encrypted contact, Luke prefers people email first and then move to Signal.

## Verifying a deploy

- Build status: `gh api repos/lkowalcz/lkowalcz.github.io/pages/builds/latest`
- Live site: `https://lukekowalczyk.com` (allow for Cloudflare cache, `max-age=600`)
