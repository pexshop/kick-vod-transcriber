export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };
    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (url.pathname === "/api/health") {
      return Response.json({ ok: true, service: "kick-vod-transcriber", extractorConfigured: Boolean(env.EXTRACTOR_URL) }, { headers: cors });
    }
    if (url.pathname === "/api/transcribe" && request.method === "POST") {
      if (!env.EXTRACTOR_URL) return Response.json({ error: "The extraction service is not configured yet. Deploy the extractor and set EXTRACTOR_URL." }, { status: 503, headers: cors });
      let body;
      try { body = await request.json(); } catch { return Response.json({ error: "Invalid JSON body." }, { status: 400, headers: cors }); }
      if (typeof body.url !== "string" || !/^https?:\/\/(www\.)?kick\.com\//i.test(body.url)) {
        return Response.json({ error: "Enter a valid public Kick VOD URL." }, { status: 400, headers: cors });
      }
      try {
        const upstream = await fetch(new URL("/transcribe", env.EXTRACTOR_URL), {
          method: "POST",
          headers: { "Content-Type": "application/json", ...(env.EXTRACTOR_TOKEN ? { "Authorization": `Bearer ${env.EXTRACTOR_TOKEN}` } : {}) },
          body: JSON.stringify({ url: body.url, translate_to: body.translate_to || null }),
          signal: AbortSignal.timeout(1000 * 60 * 10),
        });
        const data = await upstream.json().catch(() => ({ error: "Extractor returned an invalid response." }));
        return Response.json(data, { status: upstream.status, headers: cors });
      } catch {
        return Response.json({ error: "Could not reach the extraction service. Check its deployment and logs." }, { status: 502, headers: cors });
      }
    }
    if (env.ASSETS) return env.ASSETS.fetch(request);
    return new Response("Kick VOD Transcriber API is running.", { headers: cors });
  },
};