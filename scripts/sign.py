#!/usr/bin/env python3
"""Wrap an offsets payload in an ed25519-signed envelope the FUMETSU DLL verifies.

Envelope (served as fumetsu.cc/data.json and offsets/latest.json):
  {
    "alg": "EdDSA",
    "kid": "45d4bb8bafbf9ee0",
    "build": <int>,
    "steam_buildid": "<str>",
    "payload_b64": "<base64(payload.json bytes)>",
    "sig_b64": "<base64(ed25519(payload.json bytes))>"
  }

The DLL base64-decodes payload_b64, verifies sig_b64 over those exact bytes with
the embedded public key, checks kid + build, then parses the bytes as JSON. No
canonicalization needed: the signed bytes ARE the bytes the DLL parses.

Private key: env OFFSET_SIGNING_KEY = base64 of the 32-byte ed25519 seed
(GitHub Actions secret). Never commit it.

  OFFSET_SIGNING_KEY=... python sign.py --payload payload.json --out latest.json
"""
import argparse, base64, json, os, sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey)
from cryptography.hazmat.primitives import serialization, hashes

KID = "45d4bb8bafbf9ee0"  # sha256(pubkey)[:16]; must match kOffsetKid in the DLL


def load_sk():
    b64 = os.environ.get("OFFSET_SIGNING_KEY", "").strip()
    if not b64:
        print("OFFSET_SIGNING_KEY not set", file=sys.stderr)
        sys.exit(3)
    seed = base64.b64decode(b64)
    if len(seed) != 32:
        print("OFFSET_SIGNING_KEY must decode to 32 bytes", file=sys.stderr)
        sys.exit(3)
    return Ed25519PrivateKey.from_private_bytes(seed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    payload_bytes = open(a.payload, "rb").read()
    meta = json.loads(payload_bytes)

    sk = load_sk()
    sig = sk.sign(payload_bytes)

    # self-check: verify before we write anything
    sk.public_key().verify(sig, payload_bytes)

    envelope = {
        "alg": "EdDSA",
        "kid": KID,
        "build": meta["build"],
        "steam_buildid": meta["steam_buildid"],
        "payload_b64": base64.b64encode(payload_bytes).decode(),
        "sig_b64": base64.b64encode(sig).decode(),
    }
    json.dump(envelope, open(a.out, "w", encoding="utf-8"), indent=2)
    print(f"signed build {meta['build']} -> {a.out} (kid {KID})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
