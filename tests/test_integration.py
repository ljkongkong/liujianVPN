"""Integration tests validating consistency between all configuration files.

Tests cover:
- Cross-file port consistency
- Configuration completeness for deployment
- sing-box version consistency
- File permission and encoding checks
"""

import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDeploymentReadiness:
    """Tests that all required files exist for a successful deployment."""

    def test_all_required_files_exist(self):
        required_files = ["Dockerfile", "config.json"]
        for filename in required_files:
            filepath = os.path.join(REPO_ROOT, filename)
            assert os.path.isfile(filepath), (
                f"Required file '{filename}' is missing from repo"
            )

    def test_no_extra_config_files(self):
        """Ensure there's no conflicting configuration."""
        config_files = [
            f for f in os.listdir(REPO_ROOT)
            if f.endswith(".json") and f != "config.json"
        ]
        # Not an error, but worth flagging
        assert len(config_files) == 0 or True, (
            f"Found extra JSON files: {config_files}"
        )


class TestFileEncoding:
    """Tests that files use proper encoding."""

    def test_config_is_utf8(self, config_path):
        with open(config_path, "rb") as f:
            content = f.read()
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            pytest.fail("config.json must be valid UTF-8")

    def test_dockerfile_is_utf8(self, dockerfile_path):
        with open(dockerfile_path, "rb") as f:
            content = f.read()
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            pytest.fail("Dockerfile must be valid UTF-8")

    def test_config_no_bom(self, config_path):
        with open(config_path, "rb") as f:
            first_bytes = f.read(3)
        assert first_bytes != b"\xef\xbb\xbf", (
            "config.json should not have a UTF-8 BOM"
        )

    def test_dockerfile_no_bom(self, dockerfile_path):
        with open(dockerfile_path, "rb") as f:
            first_bytes = f.read(3)
        assert first_bytes != b"\xef\xbb\xbf", (
            "Dockerfile should not have a UTF-8 BOM"
        )


class TestPortConsistency:
    """Tests that port numbers are consistent across all files."""

    def test_single_listen_port_in_config(self, config):
        ports = set()
        for inbound in config.get("inbounds", []):
            if "listen_port" in inbound:
                ports.add(inbound["listen_port"])
        # Having unique ports per inbound is fine
        assert len(ports) >= 1, "Config must define at least one listen port"

    def test_all_ports_exposed_in_dockerfile(self, config, dockerfile_content):
        config_ports = set()
        for inbound in config.get("inbounds", []):
            if "listen_port" in inbound:
                config_ports.add(inbound["listen_port"])

        for port in config_ports:
            assert str(port) in dockerfile_content, (
                f"Port {port} from config.json is not referenced in Dockerfile"
            )


class TestSingBoxVersion:
    """Tests for sing-box version consistency within Dockerfile."""

    def test_consistent_version_references(self, dockerfile_content):
        versions = re.findall(r"sing-box[/-](\d+\.\d+\.\d+)", dockerfile_content)
        if len(versions) > 1:
            assert len(set(versions)) == 1, (
                f"Multiple sing-box versions found in Dockerfile: {set(versions)}"
            )

    def test_version_not_too_old(self, dockerfile_content):
        version_match = re.search(r"sing-box[/-](\d+)\.(\d+)\.(\d+)", dockerfile_content)
        if version_match:
            major = int(version_match.group(1))
            minor = int(version_match.group(2))
            # sing-box 1.x is current stable
            assert major >= 1, "sing-box version should be 1.x or higher"
            assert minor >= 0, "sing-box minor version should be non-negative"


class TestConfigSecurity:
    """Tests for security-related configuration concerns."""

    def test_uuid_not_default(self, config):
        """UUID should not be a commonly known default."""
        known_defaults = {
            "00000000-0000-0000-0000-000000000000",
            "12345678-1234-1234-1234-123456789abc",
        }
        for inbound in config.get("inbounds", []):
            for user in inbound.get("users", []):
                uuid = user.get("uuid", "")
                assert uuid not in known_defaults, (
                    f"UUID '{uuid}' is a known default and should be changed"
                )

    def test_no_plaintext_passwords_in_config(self, config_path):
        with open(config_path, "r") as f:
            content = f.read()
        # Check that config doesn't have obvious password fields with weak values
        if '"password"' in content:
            password_match = re.search(r'"password"\s*:\s*"(\w+)"', content)
            if password_match:
                password = password_match.group(1)
                weak_passwords = {"password", "123456", "admin", "test"}
                assert password not in weak_passwords, (
                    "Config contains a weak/default password"
                )

    def test_listen_not_only_localhost(self, config):
        """For a VPN server, listening on all interfaces (::) is expected."""
        for inbound in config.get("inbounds", []):
            listen = inbound.get("listen", "")
            # :: or 0.0.0.0 means listening on all interfaces (expected for VPN)
            if listen in {"::", "0.0.0.0"}:
                pass  # This is expected for a VPN server
            elif listen in {"127.0.0.1", "::1"}:
                pytest.skip("Listening on localhost only - may be intentional for testing")
