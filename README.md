# Kick VOD Transcriber

An English-language web app for submitting a public Kick VOD URL and receiving a transcript, optional translation, and summary.

## Architecture

- **Cloudflare Worker** serves the static UI and forwards requests.
- **Render Web Service** runs the Docker-based extractor (Python, yt-dlp, FFmpeg).
- **OpenAI API** provides speech transcription, optional translation, and summaries.

The extractor is deployed separately from the Worker. The app is not ready for public use until both services and their secrets are configured.

## Deploy the extractor on Render (free plan)

1. Push this repository to GitHub (it is already named `pexshop/kick-vod-transcriber`).
2. Sign in to Render and choose **New → Blueprint**.
3. Connect this GitHub repository and let Render detect `render.yaml`.
4. In the Blueprint environment-variable prompt, enter your OpenAI API key for `OPENAI_API_KEY` and create a long random value for `EXTRACTOR_TOKEN`. Use the same token later in Cloudflare. Never commit either secret or paste them into public files.
5. Deploy the Blueprint. Wait for the service to become **Live**.
6. Copy the service's public HTTPS URL (for example, `https://your-service.onrender.com`). Test `https://your-service.onrender.com/health`; it should return JSON with `ok: true`.

Render's free service may sleep when idle and take time to wake up. Free resources and request limits can also make long VODs or lengthy transcriptions fail. This is a starter deployment, not a guaranteed always-on production service.

## Connect the extractor to Cloudflare Worker

In Cloudflare Dashboard:

1. Open **Workers & Pages → kick-vod-transcriber → Settings → Variables and Secrets**.
2. Add a plain-text variable named `EXTRACTOR_URL` and set it to the Render service base URL, without adding `/transcribe`.
3. Add a secret named `EXTRACTOR_TOKEN` and paste the exact same token used in Render.
4. Save and redeploy the Worker if the dashboard requests it.

Then open `https://YOUR-WORKER-DOMAIN/api/health`. The response should show `"extractorConfigured": true`.

## Deploy the Cloudflare Worker

Connect the repository to Cloudflare Workers Builds, or deploy from a local environment with:

```sh
npm install
npx wrangler deploy
```

The static UI is in `public/`. The API health endpoint is `/api/health`.

## Local development

```sh
npm install
npx wrangler dev
```

## Limitations and responsible use

- Only submit public VODs you are authorized to access and process.
- Private, login-gated, DRM-protected, deleted, or otherwise restricted content is unsupported. Do not attempt to bypass access controls.
- Kick may change its delivery mechanisms; yt-dlp support is not guaranteed for every VOD.
- The starter currently limits VOD duration to four hours and extracted audio to 24 MB. Longer audio requires chunked transcription.
- Render free services can sleep while idle. Long-running requests may time out depending on platform limits.
- Review Kick's terms and applicable copyright/privacy laws before deployment.
- Add rate limiting, job queues, storage cleanup, and abuse prevention before exposing this service publicly.
