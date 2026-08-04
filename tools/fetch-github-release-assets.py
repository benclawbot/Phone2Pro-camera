#!/usr/bin/env python3
"""Fetch and independently verify a GitHub release asset manifest.

The metadata-only mode records the exact release and asset inventory without
claiming that any asset bytes have been verified. Optional selected downloads
are hashed during transfer and re-hashed from disk before being marked locally
verified. Firmware bytes must be stored outside the public repository.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from typing import Any, BinaryIO

DEFAULT_REPOSITORY = "spike0en/nothing_archive"
DEFAULT_TAG = "Galaga_B4.1-260615-1653"
SCHEMA_VERSION = 1
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CHUNK_SIZE = 1024 * 1024

OpenUrl = Callable[[urllib.request.Request], Any]


def release_api_url(repository: str, tag: str) -> str:
    validate_repository(repository)
    if not isinstance(tag, str) or not tag.strip():
        raise ValueError("release tag must be non-empty")
    return (
        "https://api.github.com/repos/"
        f"{repository}/releases/tags/{urllib.parse.quote(tag, safe='')}"
    )


def validate_repository(repository: str) -> None:
    if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
        raise ValueError("repository must use owner/name syntax")
    owner, name = repository.split("/", 1)
    if owner in {".", ".."} or name in {".", ".."}:
        raise ValueError("repository must use safe owner/name syntax")


def parse_github_digest(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("GitHub asset digest must be text or null")
    algorithm, separator, digest = value.partition(":")
    if separator != ":" or algorithm != "sha256" or not SHA256.fullmatch(digest):
        raise ValueError("GitHub asset digest must be sha256:<lowercase digest>")
    return digest


def safe_asset_name(value: Any) -> str:
    if not isinstance(value, str) or not value or not value.strip():
        raise ValueError("release asset name must be non-empty")
    if "\x00" in value or "/" in value or "\\" in value:
        raise ValueError(f"unsafe release asset name: {value!r}")
    if value in {".", ".."} or pathlib.PurePosixPath(value).name != value:
        raise ValueError(f"unsafe release asset name: {value!r}")
    if len(value.encode("utf-8")) > 255:
        raise ValueError("release asset name exceeds 255 UTF-8 bytes")
    return value


def _positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _https_url(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("https://"):
        raise ValueError(f"{field} must be an HTTPS URL")
    parsed = urllib.parse.urlparse(value)
    if not parsed.netloc:
        raise ValueError(f"{field} must contain a host")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional release text fields must be text or null")
    return value


def build_manifest(
    payload: Mapping[str, Any],
    repository: str,
    tag: str,
    fetched_at: str,
) -> dict[str, Any]:
    validate_repository(repository)
    parse_timestamp(fetched_at)
    if payload.get("tag_name") != tag:
        raise ValueError("GitHub release tag does not match the requested tag")
    release_id = _positive_int(payload.get("id"), "release.id")
    release_url = _https_url(payload.get("html_url"), "release.html_url")
    api_url = _https_url(payload.get("url"), "release.url")
    assets_payload = payload.get("assets")
    if not isinstance(assets_payload, list) or not assets_payload:
        raise ValueError("GitHub release must contain at least one asset")

    assets: list[dict[str, Any]] = []
    names: set[str] = set()
    ids: set[int] = set()
    for index, raw_asset in enumerate(assets_payload):
        if not isinstance(raw_asset, Mapping):
            raise ValueError(f"assets[{index}] must be an object")
        name = safe_asset_name(raw_asset.get("name"))
        if name in names:
            raise ValueError(f"duplicate release asset name: {name}")
        names.add(name)
        asset_id = _positive_int(raw_asset.get("id"), f"assets[{index}].id")
        if asset_id in ids:
            raise ValueError(f"duplicate release asset id: {asset_id}")
        ids.add(asset_id)
        size = _positive_int(raw_asset.get("size"), f"assets[{index}].size")
        state = raw_asset.get("state")
        if state != "uploaded":
            raise ValueError(f"release asset {name} is not in uploaded state")
        github_digest = parse_github_digest(raw_asset.get("digest"))
        assets.append(
            {
                "id": asset_id,
                "name": name,
                "sizeBytes": size,
                "contentType": _optional_text(raw_asset.get("content_type")),
                "apiUrl": _https_url(raw_asset.get("url"), f"assets[{index}].url"),
                "browserDownloadUrl": _https_url(
                    raw_asset.get("browser_download_url"),
                    f"assets[{index}].browser_download_url",
                ),
                "githubReportedSha256": github_digest,
                "status": (
                    "GITHUB_REPORTED_DIGEST_NOT_LOCALLY_VERIFIED"
                    if github_digest
                    else "DIGEST_NOT_PUBLISHED_NOT_LOCALLY_VERIFIED"
                ),
            }
        )
    assets.sort(key=lambda item: item["name"])
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "METADATA_ONLY_NOT_LOCALLY_VERIFIED",
        "repository": repository,
        "tag": tag,
        "fetchedAt": fetched_at,
        "release": {
            "id": release_id,
            "name": _optional_text(payload.get("name")),
            "htmlUrl": release_url,
            "apiUrl": api_url,
            "publishedAt": _optional_text(payload.get("published_at")),
            "draft": bool(payload.get("draft")),
            "prerelease": bool(payload.get("prerelease")),
        },
        "assetCount": len(assets),
        "allGithubDigestsPresent": all(
            asset["githubReportedSha256"] is not None for asset in assets
        ),
        "assets": assets,
        "verificationBoundary": (
            "Release metadata and GitHub-reported digests are provenance only. "
            "An asset becomes locally verified only after a selected download is "
            "hashed during transfer, re-hashed from disk, and size-checked."
        ),
    }


def fetch_release_payload(
    repository: str,
    tag: str,
    token: str | None = None,
    opener: OpenUrl = urllib.request.urlopen,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Phone2Pro-camera-firmware-indexer/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(release_api_url(repository, tag), headers=headers)
    try:
        with opener(request) as response:
            payload = json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        raise ValueError(f"failed to fetch GitHub release metadata: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("GitHub release response must be an object")
    return payload


def download_and_verify_asset(
    asset: Mapping[str, Any],
    output_dir: pathlib.Path,
    token: str | None = None,
    opener: OpenUrl = urllib.request.urlopen,
) -> dict[str, Any]:
    name = safe_asset_name(asset.get("name"))
    expected_size = _positive_int(asset.get("sizeBytes"), "asset.sizeBytes")
    url = _https_url(asset.get("browserDownloadUrl"), "asset.browserDownloadUrl")
    github_digest = asset.get("githubReportedSha256")
    if github_digest is not None and (
        not isinstance(github_digest, str) or not SHA256.fullmatch(github_digest)
    ):
        raise ValueError("asset.githubReportedSha256 must be a lowercase SHA-256 digest")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.is_symlink():
        raise ValueError("download directory cannot be a symlink")
    destination = output_dir / name
    if destination.exists():
        raise ValueError(f"refusing to overwrite existing asset: {destination}")

    headers = {"User-Agent": "Phone2Pro-camera-firmware-indexer/1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    temporary_path: pathlib.Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{name}.", suffix=".part", dir=output_dir, delete=False
        ) as handle:
            temporary_path = pathlib.Path(handle.name)
            transfer_digest, transfer_size = _copy_and_hash(opener(request), handle)
            handle.flush()
            os.fsync(handle.fileno())
        if transfer_size != expected_size:
            raise ValueError(
                f"asset size mismatch for {name}: expected {expected_size}, got {transfer_size}"
            )
        disk_digest = hash_file(temporary_path)
        if disk_digest != transfer_digest:
            raise ValueError(f"second-pass SHA-256 mismatch for {name}")
        if github_digest is not None and transfer_digest != github_digest:
            raise ValueError(f"GitHub-reported SHA-256 mismatch for {name}")
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    result = dict(asset)
    result.update(
        {
            "status": "VERIFIED_TWO_PASS_LOCAL_SHA256",
            "localRelativePath": name,
            "localSizeBytes": expected_size,
            "transferSha256": transfer_digest,
            "verificationSha256": disk_digest,
            "githubDigestMatch": (
                transfer_digest == github_digest if github_digest is not None else None
            ),
        }
    )
    return result


def _copy_and_hash(response: Any, output: BinaryIO) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            if not isinstance(chunk, (bytes, bytearray)):
                raise ValueError("asset response returned non-byte data")
            output.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    return digest.hexdigest(), size


def hash_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def verify_selected_assets(
    manifest: dict[str, Any],
    selected_names: Iterable[str],
    output_dir: pathlib.Path,
    token: str | None = None,
    opener: OpenUrl = urllib.request.urlopen,
) -> dict[str, Any]:
    selected = [safe_asset_name(name) for name in selected_names]
    if not selected:
        raise ValueError("at least one --asset is required when downloading")
    if len(selected) != len(set(selected)):
        raise ValueError("duplicate --asset selections are not allowed")
    by_name = {asset["name"]: asset for asset in manifest["assets"]}
    missing = sorted(set(selected) - set(by_name))
    if missing:
        raise ValueError(f"selected assets are absent from the release: {', '.join(missing)}")
    verified = {
        name: download_and_verify_asset(by_name[name], output_dir, token, opener)
        for name in selected
    }
    manifest = dict(manifest)
    manifest["assets"] = [verified.get(asset["name"], asset) for asset in manifest["assets"]]
    verified_count = sum(
        asset["status"] == "VERIFIED_TWO_PASS_LOCAL_SHA256"
        for asset in manifest["assets"]
    )
    manifest["locallyVerifiedAssetCount"] = verified_count
    manifest["status"] = (
        "ALL_ASSETS_VERIFIED_TWO_PASS_LOCAL_SHA256"
        if verified_count == manifest["assetCount"]
        else "PARTIAL_ASSET_VERIFICATION"
    )
    return manifest


def validate_manifest(manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("schemaVersion") != SCHEMA_VERSION:
        errors.append("manifest schemaVersion must be 1")
    try:
        validate_repository(manifest.get("repository"))  # type: ignore[arg-type]
    except ValueError as error:
        errors.append(str(error))
    if not isinstance(manifest.get("tag"), str) or not manifest.get("tag"):
        errors.append("manifest tag must be non-empty")
    try:
        parse_timestamp(str(manifest.get("fetchedAt", "")))
    except ValueError:
        errors.append("manifest fetchedAt must be a timezone-aware ISO-8601 timestamp")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        errors.append("manifest assets must be a list")
        return errors
    if manifest.get("assetCount") != len(assets):
        errors.append("manifest assetCount does not match assets length")
    names: set[str] = set()
    for index, asset in enumerate(assets):
        prefix = f"assets[{index}]"
        if not isinstance(asset, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        try:
            name = safe_asset_name(asset.get("name"))
        except ValueError as error:
            errors.append(f"{prefix}: {error}")
            continue
        if name in names:
            errors.append(f"duplicate manifest asset name: {name}")
        names.add(name)
        try:
            _positive_int(asset.get("sizeBytes"), f"{prefix}.sizeBytes")
            _https_url(asset.get("browserDownloadUrl"), f"{prefix}.browserDownloadUrl")
        except ValueError as error:
            errors.append(str(error))
        digest = asset.get("githubReportedSha256")
        if digest is not None and (
            not isinstance(digest, str) or not SHA256.fullmatch(digest)
        ):
            errors.append(f"{prefix}.githubReportedSha256 is invalid")
        if asset.get("status") == "VERIFIED_TWO_PASS_LOCAL_SHA256":
            transfer = asset.get("transferSha256")
            verification = asset.get("verificationSha256")
            if not isinstance(transfer, str) or not SHA256.fullmatch(transfer):
                errors.append(f"{prefix}.transferSha256 is invalid")
            if transfer != verification:
                errors.append(f"{prefix} two-pass SHA-256 values differ")
            if asset.get("localSizeBytes") != asset.get("sizeBytes"):
                errors.append(f"{prefix} local size differs from release metadata")
            if digest is not None and transfer != digest:
                errors.append(f"{prefix} local SHA-256 differs from GitHub digest")
    return errors


def parse_timestamp(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        timestamp = dt.datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("timestamp must be ISO-8601") from error
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return timestamp


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--fetched-at", default=None)
    parser.add_argument("--download-dir", type=pathlib.Path)
    parser.add_argument("--asset", action="append", default=[])
    parser.add_argument("--require-github-digests", action="store_true")
    args = parser.parse_args()

    if args.asset and args.download_dir is None:
        parser.error("--asset requires --download-dir")
    if args.download_dir is not None and not args.asset:
        parser.error("--download-dir requires at least one --asset")

    token = os.environ.get("GITHUB_TOKEN")
    try:
        payload = fetch_release_payload(args.repository, args.tag, token)
        manifest = build_manifest(payload, args.repository, args.tag, args.fetched_at or utc_now())
        if args.require_github_digests and not manifest["allGithubDigestsPresent"]:
            raise ValueError("one or more release assets lack a GitHub-reported digest")
        if args.download_dir is not None:
            manifest = verify_selected_assets(
                manifest, args.asset, args.download_dir, token
            )
        errors = validate_manifest(manifest)
        if errors:
            raise ValueError("; ".join(errors))
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Recorded {manifest['assetCount']} release assets; "
        f"status={manifest['status']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
