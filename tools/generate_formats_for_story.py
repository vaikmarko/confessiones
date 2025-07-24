#!/usr/bin/env python3
"""Trigger multiple format generations for an existing story.

Example:
  BASE_URL=https://sentimentalapp.com \
  python tools/generate_formats_for_story.py \
      --story VO2KEbHIvRbdZ021gAha \
      --user 9rrIK1FCLUcIzgiQ0xaQ \
      --exclude reflection,song,podcast
"""
import os, sys, argparse, time, json, requests

BASE_URL = os.getenv("BASE_URL", "https://sentimentalapp.com").rstrip("/")

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json"})

def post(path:str, payload=None, *, headers=None):
    url = f"{BASE_URL}{path}"
    resp = SESSION.post(url, json=payload or {}, headers=headers)
    if not resp.ok:
        raise RuntimeError(f"POST {path} -> {resp.status_code}: {resp.text}")
    return resp.json() if resp.text else {}

def get_supported_formats():
    try:
        data = SESSION.get(f"{BASE_URL}/api/formats/supported").json()
        return data.get("supported_formats") or []
    except Exception:
        # Fallback to static list
        return [
            'x','linkedin','instagram','facebook','song','poem','reel','fairytale',
            'reflection','article','blog_post','presentation','newsletter','podcast',
            'insights','growth_summary','journal_entry','letter'
        ]

def main():
    ap = argparse.ArgumentParser(description="Generate many formats for a story")
    ap.add_argument("--story", required=True, help="Story ID")
    ap.add_argument("--user", required=True, help="User ID (author)")
    ap.add_argument("--formats", help="Comma-separated list of formats (default: all supported)")
    ap.add_argument("--exclude", help="Comma-separated formats to skip")
    args = ap.parse_args()

    all_formats = args.formats.split(',') if args.formats else get_supported_formats()
    exclude = set((args.exclude or '').split(','))
    targets = [f for f in all_formats if f and f not in exclude]

    headers = {"X-User-ID": args.user}

    for fmt in targets:
        print(f"Generating {fmt} …", end=' ', flush=True)
        try:
            post(f"/api/stories/{args.story}/generate-format", {"format_type": fmt}, headers=headers)
            print("✓")
        except Exception as e:
            print(f"failed: {e}")
        time.sleep(0.3)

if __name__ == "__main__":
    main() 