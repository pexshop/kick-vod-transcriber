# Kick VOD Transcriber

An English-language web app for submitting a public Kick VOD URL and receiving a transcript, optional translation, and summary.

## Architecture

- **Cloudflare Worker** serves the static UI and proxies requests to the extractor.
- **Extractor API** runs separately in a container because yt-dlp and FFmpeg are not suitable for running inside a standard Cloudflare Worker.
- **OpenAI API** provides speech transcription and optional translation/summary.

This repository is a starter implementation. A successful deployment requires a separately hosted extractor service and configured secrets.

## Deploy the extractor

1. Deploy the `extractor/` directory as a Docker container on a service that supports persistent execution and outbound network access.
2. Set `OPENAI_API_KEY` in the extractor environment. Never commit API keys.
3. Set a strong `EXTRACTOR_TOKEN` in the extractor environment.
4. Expose the service over HTTPS and confirm `GET /health` responds.

Example:

```sh
docker build -t kick-vod-extractor ./extractor
docker run -p 8080:8080 -e OPENAI_API_KEY=YOUR_KEY -e EXTRACTOR_TOKEN=YOUR_LONG_RANDOM_TOKEN kick-vod-extractor
```

## Deploy the Cloudflare Worker

Install dependencies and deploy:

```sh
npm install
npx wrangler secret put EXTRACTOR_TOKEN
npx wrangler deploy
```

Set the extractor URL as a Worker variable:

```sh
npx wrangler deploy
```

In the Cloudflare Worker settings, add variable `EXTRACTOR_URL` with the HTTPS base URL of the deployed extractor. Add secret `EXTRACTOR_TOKEN` with the same token configured on the extractor.

## Local development

```sh
npm install
npx wrangler dev
``

The UI is served from `public/`. The health endpoint is `/api/health`.

## Limitations and responsible use

- Only submit public VODs that you are authorized to access and process.
- Private, login-gated, DRM-protected, deleted, or otherwise restricted content is unsupported. Do not attempt to bypass access controls.
- Kick may change its delivery mechanisms; yt-dlp support is not guaranteed for every VOD.
- The starter currently limits extracted audio to 24 MB and VOD duration to four hours. Long recordings need chunked audio processing before production use.
- Review Kick's terms and applicable copyright/privacy laws before deployment.
- Add rate limiting, job queues, storage cleanup, and abuse prevention before exposing this service publicly.
