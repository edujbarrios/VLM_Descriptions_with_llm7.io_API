#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64, mimetypes, os, re, sys, time, yaml
from typing import Any, Dict, List
from dotenv import load_dotenv
from openai import OpenAI

# --- Load config with ${ENV:default} expansion ---
_ENV = re.compile(r"\$\{([^}:]+)(?::([^}]+))?\}")
def _expand(v):
    if isinstance(v, str):
        return _ENV.sub(lambda m: os.getenv(m.group(1), m.group(2) or ""), v)
    if isinstance(v, dict): return {k:_expand(x) for k,x in v.items()}
    if isinstance(v, list): return [_expand(x) for x in v]
    return v

def load_config(path="config.yaml") -> Dict[str, Any]:
    load_dotenv(override=False)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return _expand(data)

# --- Helpers ---
def file_to_data_url(path: str) -> str:
    p = os.path.normpath(path)
    if not os.path.exists(p):
        raise FileNotFoundError(f"File does not exist: {p}")
    mime, _ = mimetypes.guess_type(p)
    if not mime: mime = "image/png"
    with open(p, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def multimodal_content(image_url: str, prompt: str) -> List[Dict[str, Any]]:
    return [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": image_url}},
    ]

# --- Main ---
def main():
    cfg = load_config()
    base_url = cfg["client"]["base_url"]
    api_key  = cfg["client"]["api_key"]
    model    = cfg["client"]["model"]
    prompt   = cfg["run"].get("prompt", "Describe the image.")
    temp     = float(cfg["run"].get("temperature", 0.0))

    img_cfg = cfg.get("image", {})
    if img_cfg.get("path"):
        image_url = file_to_data_url(img_cfg["path"])
        src = f"file:{os.path.normpath(img_cfg['path'])}"
    elif img_cfg.get("url"):
        image_url = img_cfg["url"]
        src = f"url:{img_cfg['url']}"
    else:
        print("ERROR: define image.path or image.url in config.yaml", file=sys.stderr)
        sys.exit(2)

    print("=== Vision-Language Model image description (See /models/models.md to check all avaiable models) ===")
    print(f"Base URL : {base_url}")
    print(f"Model    : {model}")
    print(f"Image    : {src}")

    client = OpenAI(base_url=base_url, api_key=api_key)
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": multimodal_content(image_url, prompt)}],
        temperature=temp,
    )
    latency = time.time() - t0

    text = (resp.choices[0].message.content or "").strip()
    print("\n=== Description ===")
    print(text if text else "(empty response)")
    print(f"\n(latency: {latency:.2f}s)")

if __name__ == "__main__":
    main()
