import os, re, tempfile, shutil
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, HttpUrl
from yt_dlp import YoutubeDL
from openai import OpenAI

app = FastAPI(title="Kick VOD Transcriber Extractor")
TOKEN = os.getenv("EXTRACTOR_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_DURATION_SECONDS = int(os.getenv("MAX_DURATION_SECONDS", "14400"))

class Job(BaseModel):
    url: HttpUrl
    translate_to: str | None = None

def check_auth(authorization: str | None):
    if not TOKEN:\n        raise HTTPException(status_code=503, detail="EXTRACTOR_TOKEN is not configured.")\n    if authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/health")
def health():
    return {"ok": True, "openaiConfigured": bool(OPENAI_API_KEY)}

@app.post("/transcribe")
def transcribe(job: Job, authorization: str | None = Header(default=None)):
    check_auth(authorization)
    url = str(job.url)
    if not re.match(r"^https?://(www\.)?kick\.com/", url, re.I):
        raise HTTPException(status_code=400, detail="Only Kick URLs are accepted.")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    with tempfile.TemporaryDirectory() as tmp:
        output = str(Path(tmp) / "audio.%(ext)s")
        opts = {"format": "bestaudio/best", "outtmpl": output, "noplaylist": True,
                "quiet": True, "no_warnings": True, "restrictfilenames": True,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "96"}]}
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                duration = info.get("duration")
                if duration and duration > MAX_DURATION_SECONDS:
                    raise HTTPException(status_code=413, detail=f"VOD is longer than the configured {MAX_DURATION_SECONDS // 3600}-hour limit.")
                ydl.download([url])
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not extract this VOD. It may be unavailable or unsupported: {str(exc)[:300]}")
        audio = next(Path(tmp).glob("audio.mp3"), None)
        if not audio or not audio.exists():
            raise HTTPException(status_code=500, detail="Audio extraction did not produce an MP3 file.")
        if audio.stat().st_size > 24 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Extracted audio exceeds the 24 MB transcription upload limit. Configure chunking for long VODs.")
        try:
            with audio.open("rb") as stream:
                transcript = client.audio.transcriptions.create(model="whisper-1", file=stream, response_format="text")
            transcript_text = str(transcript)
            translation = None
            summary = None
            if job.translate_to:
                completion = client.chat.completions.create(
                    model=os.getenv("TEXT_MODEL", "gpt-4o-mini"),
                    messages=[{"role": "system", "content": f"Translate the transcript into {job.translate_to}. Preserve speaker labels and timestamps. Return only the translation."},
                              {"role": "user", "content": transcript_text}])
                translation = completion.choices[0].message.content
            summary_completion = client.chat.completions.create(
                model=os.getenv("TEXT_MODEL", "gpt-4o-mini"),
                messages=[{"role": "system", "content": "Summarize this transcript in concise bullet points. Do not invent details."},
                          {"role": "user", "content": transcript_text}])
            summary = summary_completion.choices[0].message.content
            return {"transcript": transcript_text, "translation": translation, "summary": summary, "title": info.get("title")}
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Transcription or language processing failed: {str(exc)[:300]}")
