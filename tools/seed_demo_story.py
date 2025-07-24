#!/usr/bin/env python3
"""Seed Sentimental with a demo user, 20-message conversation, a generated story and a few formats.

Usage:
  python tools/seed_demo_story.py \
      --name "Emily" \
      --email demo1@sentimental.com \
      --prompt-file prompts/parents_are_splitting.txt

Env vars:
  BASE_URL  (default https://sentimentalapp.com)
"""
import argparse, os, sys, time, json, textwrap
import requests

BASE_URL = os.getenv("BASE_URL", "https://sentimentalapp.com").rstrip("/")

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})

def post(path, payload=None, *, headers=None):
    url = f"{BASE_URL}{path}"
    resp = SESSION.post(url, json=payload or {}, headers=headers)
    if not resp.ok:
        raise RuntimeError(f"POST {path} -> {resp.status_code}: {resp.text}")
    return resp.json()

def put(path, payload=None, *, headers=None):
    url = f"{BASE_URL}{path}"
    resp = SESSION.put(url, json=payload or {}, headers=headers)
    if not resp.ok:
        raise RuntimeError(f"PUT {path} -> {resp.status_code}: {resp.text}")
    return resp.json() if resp.text else {}


def ensure_user(name:str, email:str):
    # Attempt register (backend returns 409 if already exists)
    payload = {
        "uid": f"seed_{int(time.time())}",
        "email": email,
        "name": name,
        "emailVerified": False,
        "provider": "email"
    }
    try:
        data = post("/api/auth/register", payload)
        print("Registered new user", data["user_id"])
        return data["user_id"]
    except RuntimeError as e:
        if "409" in str(e):
            # User exists, log in to get id
            data = post("/api/auth/login", {"email": email, "password": "testpassword123"})
            print("Using existing user", data["user_id"])
            return data["user_id"]
        raise

def run_conversation(user_id:str, lines:list[str]):
    for i, line in enumerate(lines, 1):
        print(f"[{i:02}] user: {line[:60]}…")
        resp = post("/api/chat/message", {"user_id": user_id, "message": line})
        time.sleep(1)  # give backend a breather
    print("Conversation complete.")

def generate_story(user_id:str, title_hint:str|None=None, conversation:list=None):
    payload = {"user_id": user_id}
    if title_hint:
        payload["title_suggestion"] = title_hint
    if conversation:
        payload["conversation"] = conversation
    data = post("/api/stories/generate", payload)
    # API returns {'success': True, 'story': {...}}, or raw fields depending on version
    story = data.get("story") if isinstance(data, dict) else None
    story_id = story.get("id") if story else data.get("id") or data.get("story_id")
    if not story_id:
        raise RuntimeError(f"Unexpected API response: {data}")
    print("Story", story_id, "created")
    return story_id

def generate_formats(story_id:str, user_id:str, formats:list[str]):
    headers = {"X-User-ID": user_id}
    for fmt in formats:
        print("Trigger format", fmt)
        try:
            post(f"/api/stories/{story_id}/generate-format", {"format_type": fmt}, headers=headers)
        except RuntimeError as e:
            print("  - format", fmt, "failed:", e)
        time.sleep(0.5)

def make_public(story_id:str, user_id:str):
    headers = {"X-User-ID": user_id}
    put(f"/api/stories/{story_id}/privacy", {"is_public": True}, headers=headers)


def main():
    ap = argparse.ArgumentParser(description="Seed Sentimental with demo story")
    ap.add_argument("--name", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--formats", default="reflection,song,podcast")
    args = ap.parse_args()

    with open(args.prompt_file, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    if len(lines) < 20:
        print("warning: prompt has <20 lines, continuing anyway", file=sys.stderr)

    user_id = ensure_user(args.name, args.email)
    run_conversation(user_id, lines)

    # Build conversation payload of user messages only
    conversation = [{'role': 'user', 'content': line} for line in lines]
    try:
        story_id = generate_story(user_id, title_hint=lines[0][:50], conversation=conversation)
    except TypeError:
        # Backward-compat: generate_story signature unchanged, so call directly
        story_id = generate_story(user_id, title_hint=lines[0][:50])

    generate_formats(story_id, user_id, args.formats.split(","))
    make_public(story_id, user_id)

    print("Done! Story is public at /app?story=", story_id)

if __name__ == "__main__":
    main() 