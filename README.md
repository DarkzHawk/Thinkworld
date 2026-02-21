# Personal Archive Docker App (MVP)

## Overview
- Article: save cleaned HTML and attempt to download embedded images.
- Image/file: download and store.
- Video: download only if allowlisted *and* a direct file without DRM or streaming manifests. Otherwise metadata only.

Policy notes:
- YouTube is always metadata-only due to policy/DRM risk.
- If the URL is an m3u8/mpd or shows DRM/token/encryption signs, the worker stops and stores metadata only.

## Setup
1. Copy `.env.example` to `.env` and edit as needed.
2. Ensure host volume `/data` exists on the NAS.

## QNAP Container Station volume mount
- In Container Station, map the host path `/data` to container path `/data`.
- This keeps all archived files persistent across container updates.

## Run
```
docker-compose up -d --build
```

## E2E test (curl)
```
# create item
curl -X POST http://localhost:8000/api/items \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "tags": ["sample"]}'

# list/search
curl "http://localhost:8000/api/items?query=example&tag=sample"

# detail
curl http://localhost:8000/api/items/1
```

## UI
- Open `http://localhost:8000/` for the simple UI.

## Data directories
- Files: `/data/files`
- HTML: `/data/html`
