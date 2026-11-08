"""Upload a video to YouTube as PRIVATE via the YouTube Data API v3 (resumable upload).

Credentials come from environment variables only (never commit them):
    YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN

One-time setup (owner does this once, ~10 min):
  1. console.cloud.google.com → new project → enable "YouTube Data API v3".
  2. OAuth consent screen (External, Testing) → add your own Google account as a test user.
  3. Credentials → OAuth client ID → type "Desktop app" → copy client id + secret.
  4. Locally:  pip install google-auth-oauthlib   then
         python yt_upload.py --auth CLIENT_ID CLIENT_SECRET
     → opens a browser, pick the channel's Google account, prints the refresh token.
  5. Store the three values as secrets where the scheduled task can read them.

Upload:
    python yt_upload.py --video out/ep001/video.mp4 --meta out/ep001.json --thumb out/ep001/video_thumb.jpg
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def access_token():
    import requests
    cid, sec, rt = (os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and sec and rt):
        sys.exit("missing YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN")
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": cid, "client_secret": sec, "refresh_token": rt, "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def upload(video, meta, thumb=None, privacy="private"):
    import requests
    tok = access_token()
    h = {"Authorization": f"Bearer {tok}"}
    body = {
        "snippet": {"title": meta["title"][:100], "description": meta["description"][:4900],
                    "tags": meta.get("tags", [])[:30], "categoryId": "10", "defaultLanguage": "en"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False, "embeddable": True},
    }
    size = os.path.getsize(video)
    r = requests.post(UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"},
                      headers={**h, "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"},
                      data=json.dumps(body), timeout=60)
    r.raise_for_status()
    session = r.headers["Location"]
    # upload in 32 MB chunks so a flaky connection can resume
    chunk = 32 * 1024 * 1024
    sent = 0
    with open(video, "rb") as f:
        while sent < size:
            f.seek(sent)
            data = f.read(chunk)
            end = sent + len(data) - 1
            for attempt in range(5):
                try:
                    rr = requests.put(session, headers={**h, "Content-Length": str(len(data)),
                                                        "Content-Range": f"bytes {sent}-{end}/{size}"},
                                      data=data, timeout=600)
                    if rr.status_code in (200, 201):
                        vid = rr.json()["id"]
                        sent = size
                        break
                    if rr.status_code == 308:
                        sent = end + 1
                        break
                    rr.raise_for_status()
                except Exception as e:  # noqa: BLE001
                    if attempt == 4:
                        raise
                    time.sleep(2 ** attempt)
            print(f"  uploaded {sent / size:.0%}", flush=True)
    if thumb and os.path.exists(thumb):
        with open(thumb, "rb") as f:
            t = requests.post(f"{API}/thumbnails/set", params={"videoId": vid}, headers={**h, "Content-Type": "image/jpeg"},
                              data=f.read(), timeout=120)
            if t.status_code >= 300:
                print("thumbnail failed:", t.text[:200])
    print(f"https://studio.youtube.com/video/{vid}/edit")
    return vid


def auth_flow(client_id, client_secret):
    from google_auth_oauthlib.flow import InstalledAppFlow
    cfg = {"installed": {"client_id": client_id, "client_secret": client_secret,
                         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                         "token_uri": "https://oauth2.googleapis.com/token"}}
    flow = InstalledAppFlow.from_client_config(cfg, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    print("\nYT_REFRESH_TOKEN=" + creds.refresh_token)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth", nargs=2, metavar=("CLIENT_ID", "CLIENT_SECRET"))
    ap.add_argument("--video")
    ap.add_argument("--meta")
    ap.add_argument("--thumb")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    a = ap.parse_args()
    if a.auth:
        auth_flow(*a.auth)
    else:
        if a.privacy == "public":
            sys.exit("refusing: public uploads need the owner's explicit OK (PLAYBOOK rule)")
        with open(a.meta) as f:
            m = json.load(f)
        upload(a.video, m, a.thumb, a.privacy)
