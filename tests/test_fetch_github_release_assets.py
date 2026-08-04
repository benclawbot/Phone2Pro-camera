from __future__ import annotations

import hashlib
import importlib.util
import io
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "fetch-github-release-assets.py"
SPEC = importlib.util.spec_from_file_location("fetch_github_release_assets", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ByteResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


class GitHubReleaseAssetTest(unittest.TestCase):
    def payload(self):
        first = b"system-image"
        second = b"vendor-image"
        return {
            "id": 77,
            "tag_name": MODULE.DEFAULT_TAG,
            "name": "Galaga images",
            "html_url": "https://github.com/spike0en/nothing_archive/releases/tag/"
            + MODULE.DEFAULT_TAG,
            "url": "https://api.github.com/repos/spike0en/nothing_archive/releases/77",
            "published_at": "2026-06-20T12:00:00Z",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "id": 1002,
                    "name": "vendor.img",
                    "size": len(second),
                    "content_type": "application/octet-stream",
                    "state": "uploaded",
                    "url": "https://api.github.com/repos/x/y/releases/assets/1002",
                    "browser_download_url": "https://github.com/x/y/releases/download/t/vendor.img",
                    "digest": "sha256:" + hashlib.sha256(second).hexdigest(),
                },
                {
                    "id": 1001,
                    "name": "system.img",
                    "size": len(first),
                    "content_type": "application/octet-stream",
                    "state": "uploaded",
                    "url": "https://api.github.com/repos/x/y/releases/assets/1001",
                    "browser_download_url": "https://github.com/x/y/releases/download/t/system.img",
                    "digest": None,
                },
            ],
        }

    def manifest(self):
        return MODULE.build_manifest(
            self.payload(),
            MODULE.DEFAULT_REPOSITORY,
            MODULE.DEFAULT_TAG,
            "2026-08-04T22:45:00+02:00",
        )

    def test_builds_sorted_metadata_only_manifest_without_overclaim(self):
        manifest = self.manifest()
        self.assertEqual("METADATA_ONLY_NOT_LOCALLY_VERIFIED", manifest["status"])
        self.assertEqual(["system.img", "vendor.img"], [a["name"] for a in manifest["assets"]])
        self.assertFalse(manifest["allGithubDigestsPresent"])
        self.assertEqual(
            "DIGEST_NOT_PUBLISHED_NOT_LOCALLY_VERIFIED",
            manifest["assets"][0]["status"],
        )
        self.assertEqual([], MODULE.validate_manifest(manifest))

    def test_requested_tag_must_match_release(self):
        payload = self.payload()
        payload["tag_name"] = "wrong"
        with self.assertRaisesRegex(ValueError, "does not match"):
            MODULE.build_manifest(
                payload,
                MODULE.DEFAULT_REPOSITORY,
                MODULE.DEFAULT_TAG,
                "2026-08-04T20:45:00Z",
            )

    def test_unsafe_and_duplicate_asset_names_are_rejected(self):
        payload = self.payload()
        payload["assets"][0]["name"] = "../vendor.img"
        with self.assertRaisesRegex(ValueError, "unsafe release asset name"):
            MODULE.build_manifest(
                payload,
                MODULE.DEFAULT_REPOSITORY,
                MODULE.DEFAULT_TAG,
                "2026-08-04T20:45:00Z",
            )
        payload = self.payload()
        payload["assets"][1]["name"] = "vendor.img"
        with self.assertRaisesRegex(ValueError, "duplicate release asset name"):
            MODULE.build_manifest(
                payload,
                MODULE.DEFAULT_REPOSITORY,
                MODULE.DEFAULT_TAG,
                "2026-08-04T20:45:00Z",
            )

    def test_invalid_or_non_sha256_github_digest_is_rejected(self):
        payload = self.payload()
        payload["assets"][0]["digest"] = "sha1:abcd"
        with self.assertRaisesRegex(ValueError, "sha256"):
            MODULE.build_manifest(
                payload,
                MODULE.DEFAULT_REPOSITORY,
                MODULE.DEFAULT_TAG,
                "2026-08-04T20:45:00Z",
            )

    def test_selected_asset_is_hashed_during_download_and_from_disk(self):
        content = b"vendor-image"
        manifest = self.manifest()

        def opener(request):
            self.assertTrue(request.full_url.startswith("https://"))
            return ByteResponse(content)

        with tempfile.TemporaryDirectory() as temporary:
            verified = MODULE.verify_selected_assets(
                manifest,
                ["vendor.img"],
                pathlib.Path(temporary),
                opener=opener,
            )
            path = pathlib.Path(temporary) / "vendor.img"
            self.assertEqual(content, path.read_bytes())

        asset = next(a for a in verified["assets"] if a["name"] == "vendor.img")
        expected = hashlib.sha256(content).hexdigest()
        self.assertEqual("VERIFIED_TWO_PASS_LOCAL_SHA256", asset["status"])
        self.assertEqual(expected, asset["transferSha256"])
        self.assertEqual(expected, asset["verificationSha256"])
        self.assertTrue(asset["githubDigestMatch"])
        self.assertEqual("PARTIAL_ASSET_VERIFICATION", verified["status"])
        self.assertEqual([], MODULE.validate_manifest(verified))

    def test_size_mismatch_removes_partial_download(self):
        manifest = self.manifest()
        asset = next(a for a in manifest["assets"] if a["name"] == "vendor.img")

        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            with self.assertRaisesRegex(ValueError, "size mismatch"):
                MODULE.download_and_verify_asset(
                    asset,
                    directory,
                    opener=lambda request: ByteResponse(b"short"),
                )
            self.assertEqual([], list(directory.iterdir()))

    def test_download_requires_explicit_known_unique_asset_names(self):
        manifest = self.manifest()
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            with self.assertRaisesRegex(ValueError, "at least one"):
                MODULE.verify_selected_assets(manifest, [], directory)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                MODULE.verify_selected_assets(
                    manifest, ["system.img", "system.img"], directory
                )
            with self.assertRaisesRegex(ValueError, "absent from the release"):
                MODULE.verify_selected_assets(manifest, ["missing.img"], directory)

    def test_repository_and_timestamp_validation(self):
        with self.assertRaisesRegex(ValueError, "owner/name"):
            MODULE.release_api_url("not-a-repository", MODULE.DEFAULT_TAG)
        with self.assertRaisesRegex(ValueError, "timezone"):
            MODULE.build_manifest(
                self.payload(),
                MODULE.DEFAULT_REPOSITORY,
                MODULE.DEFAULT_TAG,
                "2026-08-04T20:45:00",
            )


if __name__ == "__main__":
    unittest.main()
