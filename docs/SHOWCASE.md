# Showcase Demo Hub

## Purpose
`showcase/` is the public-facing static site used to demo SkillBench-PD quickly to:
- non-technical stakeholders,
- technical evaluators,
- hands-on users who want to run the benchmark.

## User Journeys
- `index.html` (`Demo Hub`): high-level orientation and call-to-action links.
- `non-technical.html` (`Why It Matters`): business framing and pitch narrative.
- `technical.html` (`How It Works`): architecture and implementation details.
- `evidence.html` (`Evidence`): sample metrics/charts plus a reproducible command.

## Data Refresh Flow
The evidence page reads from `showcase/data/evidence.json`, generated from committed sample artifacts.

```bash
uv run python scripts/build_showcase_data.py
```

## Local Preview
```bash
uv run python -m http.server 8123 -d showcase
```

Then open <http://localhost:8123>.

## Vercel Deploy
```bash
vercel deploy showcase --prod
```

Production alias:
- <https://showcase-jlov7s-projects.vercel.app>

If the URL returns a `401`, disable Vercel deployment protection for this project before sharing publicly.
