# lkowalcz.github.io

Personal website of Luke (Lucas) Kowalczyk. Plain static HTML — no build step, no framework, no Jekyll.

## Hosting setup

- **GitHub Pages** user site: published from the `main` branch, root directory, of `lkowalcz/lkowalcz.github.io`. Every push to `main` deploys automatically — there is no CI config to maintain.
- **Custom domain:** `lukekowalczyk.com` (note: Luke, not Lucas), set via the `CNAME` file in the repo root. Do not delete or rename `CNAME` — that disconnects the domain. HTTPS is enforced in the GitHub Pages settings.
- **DNS / CDN:** the domain's DNS is managed by **Cloudflare**, which proxies traffic in front of GitHub Pages (the domain resolves to Cloudflare IPs, not GitHub's). Cloudflare's "Automatic HTTPS Rewrites" is active, and responses are cached briefly — a deployed change may take a few minutes to appear.
- **`.nojekyll`** (empty file) tells GitHub Pages to serve the files as-is instead of running the legacy Jekyll pipeline. Keep it.

## Site structure

- `index.html` — the entire site: one page with About / Research / Contact sections, toggled by a small vanilla-JS script at the end of `<body>` (no dependencies). Sections and photos are `.collapsible` divs; toggling adds/removes the `.collapsed` class, and a CSS `grid-template-rows` transition animates the slide. Clicking the photo swaps between two pictures (`images/me.png`, `images/pic2.jpg`).
- `stylesheet.css` — all styling, including the `.collapsible` animation, link-styled `<button>`s (`.linklike`), and a ≤600px media query for phones.
- `favicon.svg` — "LK" monogram favicon.
- `luke_columbia_pgp.asc` — PGP public key, linked from the Contact section.
- Email addresses in `index.html` are plain `mailto:` links in the Contact section.

## Verifying a deploy

- Build status: `gh api repos/lkowalcz/lkowalcz.github.io/pages/builds/latest`
- Live site: `https://lukekowalczyk.com` (allow for Cloudflare cache, `max-age=600`)
