#!/usr/bin/env python3
"""Validate repository text identity across deterministic LF/CRLF checkouts."""

from __future__ import annotations

import hashlib
from pathlib import Path


def repository_text_bytes(path: Path) -> bytes:
    """Return governed LF bytes for an exact LF or exact CRLF checkout."""

    data = path.read_bytes()
    if b"\r" not in data:
        return data

    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized or normalized.replace(b"\n", b"\r\n") != data:
        raise RuntimeError(
            f"Repository evidence is not a deterministic LF or CRLF checkout: {path}"
        )
    return normalized


def repository_text_sha256(path: Path, *, uppercase: bool = False) -> str:
    digest = hashlib.sha256(repository_text_bytes(path)).hexdigest()
    return digest.upper() if uppercase else digest


def windows_crlf_projection_sha256(
    path: Path,
    *,
    uppercase: bool = False,
) -> str:
    repository_bytes = repository_text_bytes(path)
    digest = hashlib.sha256(
        repository_bytes.replace(b"\n", b"\r\n")
    ).hexdigest()
    return digest.upper() if uppercase else digest
