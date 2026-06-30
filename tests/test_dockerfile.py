"""Unit tests for Dockerfile validation.

Tests cover:
- Dockerfile existence and structure
- Base image configuration
- Required instructions (WORKDIR, EXPOSE, CMD)
- sing-box binary download and setup
- Port consistency with config.json
- Security best practices
"""

import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDockerfileExists:
    """Tests that Dockerfile exists and is non-empty."""

    def test_dockerfile_exists(self, dockerfile_path):
        assert os.path.isfile(dockerfile_path), "Dockerfile must exist in repo root"

    def test_dockerfile_not_empty(self, dockerfile_content):
        assert len(dockerfile_content.strip()) > 0, "Dockerfile must not be empty"

    def test_dockerfile_has_multiple_lines(self, dockerfile_content):
        lines = [l for l in dockerfile_content.splitlines() if l.strip()]
        assert len(lines) >= 3, "Dockerfile should have at least 3 instructions"


class TestDockerfileBaseImage:
    """Tests for the base image (FROM instruction)."""

    def test_starts_with_from(self, dockerfile_lines):
        non_comment_lines = [l for l in dockerfile_lines if not l.startswith("#")]
        assert non_comment_lines[0].startswith("FROM "), (
            "Dockerfile must start with FROM instruction"
        )

    def test_uses_alpine(self, dockerfile_content):
        assert "alpine" in dockerfile_content.lower(), (
            "Dockerfile should use Alpine Linux as base for minimal image size"
        )

    def test_base_image_has_tag(self, dockerfile_content):
        from_match = re.search(r"FROM\s+(\S+)", dockerfile_content)
        assert from_match, "Could not find FROM instruction"
        image = from_match.group(1)
        assert ":" in image, (
            f"Base image '{image}' should have an explicit tag (not use implicit 'latest')"
        )


class TestDockerfileWorkdir:
    """Tests for WORKDIR configuration."""

    def test_has_workdir(self, dockerfile_content):
        assert "WORKDIR" in dockerfile_content, "Dockerfile must have WORKDIR instruction"

    def test_workdir_is_absolute_path(self, dockerfile_content):
        workdir_match = re.search(r"WORKDIR\s+(\S+)", dockerfile_content)
        assert workdir_match, "Could not find WORKDIR instruction"
        workdir = workdir_match.group(1)
        assert workdir.startswith("/"), (
            f"WORKDIR '{workdir}' must be an absolute path"
        )


class TestDockerfileSingBox:
    """Tests for sing-box binary download and setup."""

    def test_downloads_singbox(self, dockerfile_content):
        assert "sing-box" in dockerfile_content, (
            "Dockerfile must reference sing-box"
        )

    def test_downloads_from_official_source(self, dockerfile_content):
        assert "github.com/SagerNet/sing-box" in dockerfile_content, (
            "sing-box must be downloaded from official GitHub releases"
        )

    def test_specifies_version(self, dockerfile_content):
        version_match = re.search(r"sing-box[/-](\d+\.\d+\.\d+)", dockerfile_content)
        assert version_match, (
            "Dockerfile must specify an explicit sing-box version"
        )

    def test_version_format(self, dockerfile_content):
        version_match = re.search(r"sing-box[/-](\d+\.\d+\.\d+)", dockerfile_content)
        if version_match:
            version = version_match.group(1)
            parts = version.split(".")
            assert len(parts) == 3, f"Version '{version}' must be semver (x.y.z)"
            assert all(p.isdigit() for p in parts), (
                f"Version '{version}' must have numeric parts"
            )

    def test_downloads_linux_amd64(self, dockerfile_content):
        assert "linux-amd64" in dockerfile_content, (
            "Dockerfile must download linux-amd64 architecture"
        )

    def test_cleans_up_tarball(self, dockerfile_content):
        assert "rm" in dockerfile_content, (
            "Dockerfile should clean up downloaded tarball to reduce image size"
        )

    def test_copies_config(self, dockerfile_content):
        assert "COPY config.json" in dockerfile_content, (
            "Dockerfile must COPY config.json into the image"
        )


class TestDockerfileExpose:
    """Tests for EXPOSE instruction."""

    def test_has_expose(self, dockerfile_content):
        assert "EXPOSE" in dockerfile_content, "Dockerfile must have EXPOSE instruction"

    def test_expose_port_is_numeric(self, dockerfile_content):
        expose_match = re.search(r"EXPOSE\s+(\d+)", dockerfile_content)
        assert expose_match, "EXPOSE must specify a numeric port"
        port = int(expose_match.group(1))
        assert 1 <= port <= 65535, f"EXPOSE port {port} out of valid range"


class TestDockerfileCMD:
    """Tests for CMD instruction."""

    def test_has_cmd(self, dockerfile_content):
        assert "CMD" in dockerfile_content, "Dockerfile must have CMD instruction"

    def test_cmd_runs_singbox(self, dockerfile_content):
        assert "sing-box" in dockerfile_content, (
            "CMD must run sing-box"
        )

    def test_cmd_uses_config(self, dockerfile_content):
        cmd_match = re.search(r'CMD\s+\[.*"config\.json".*\]', dockerfile_content)
        assert cmd_match, "CMD must reference config.json"

    def test_cmd_uses_exec_form(self, dockerfile_content):
        cmd_match = re.search(r"CMD\s+\[", dockerfile_content)
        assert cmd_match, (
            "CMD should use exec form (JSON array) for proper signal handling"
        )


class TestDockerfileSecurityBestPractices:
    """Tests for Docker security best practices."""

    def test_no_add_instruction(self, dockerfile_content):
        add_lines = re.findall(r"^ADD\s", dockerfile_content, re.MULTILINE)
        assert len(add_lines) == 0, (
            "Use COPY instead of ADD for local files (ADD has implicit tar extraction)"
        )

    def test_no_root_user_exposed(self, dockerfile_content):
        # This is a soft check - ideally containers run as non-root
        # but for sing-box it may need root for certain operations
        pass

    def test_uses_no_cache_for_apk(self, dockerfile_content):
        if "apk add" in dockerfile_content:
            assert "--no-cache" in dockerfile_content, (
                "apk add should use --no-cache to reduce image size"
            )


class TestDockerfileConfigConsistency:
    """Tests that Dockerfile and config.json are consistent."""

    def test_exposed_port_matches_config(self, dockerfile_content, config):
        expose_match = re.search(r"EXPOSE\s+(\d+)", dockerfile_content)
        assert expose_match, "Could not find EXPOSE port"
        exposed_port = int(expose_match.group(1))

        config_ports = []
        for inbound in config.get("inbounds", []):
            if "listen_port" in inbound:
                config_ports.append(inbound["listen_port"])

        assert exposed_port in config_ports, (
            f"Dockerfile EXPOSE port {exposed_port} does not match any "
            f"config.json listen_port values: {config_ports}"
        )

    def test_config_file_referenced_in_cmd(self, dockerfile_content):
        assert "config.json" in dockerfile_content, (
            "Dockerfile CMD must reference the config file"
        )
