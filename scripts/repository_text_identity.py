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


def repository_text_identity_matches(
    path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
) -> bool:
    """Match a frozen LF or Windows-CRLF identity from either checkout."""

    expected_digest = expected_sha256.lower()

    def matches(content: bytes) -> bool:
        return (
            len(content) == expected_bytes
            and hashlib.sha256(content).hexdigest() == expected_digest
        )

    return any(
        matches(content)
        for content in repository_text_identity_candidates(path)
    )


def repository_text_identity_candidates(path: Path) -> tuple[bytes, ...]:
    """Return raw and deterministic LF/CRLF identities without duplicates."""

    raw = path.read_bytes()
    candidates = [raw]
    try:
        repository_bytes = repository_text_bytes(path)
    except RuntimeError:
        return tuple(candidates)
    for candidate in (
        repository_bytes,
        repository_bytes.replace(b"\n", b"\r\n"),
    ):
        if candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)


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
