"""Unit tests for config.json validation.

Tests cover:
- JSON structure and parsing
- Required top-level fields
- Inbound configuration (type, listen address, port, users, transport)
- Outbound configuration
- UUID format validation
- Network settings consistency
"""

import json
import re
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


class TestConfigFileValidity:
    """Tests that config.json is valid JSON and can be loaded."""

    def test_config_file_exists(self, config_path):
        assert os.path.isfile(config_path), "config.json must exist in repo root"

    def test_config_is_valid_json(self, config_path):
        with open(config_path, "r") as f:
            content = f.read()
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            pytest.fail(f"config.json is not valid JSON: {e}")

    def test_config_is_dict(self, config):
        assert isinstance(config, dict), "config.json root must be a JSON object"

    def test_config_not_empty(self, config):
        assert len(config) > 0, "config.json must not be empty"


class TestConfigLogSection:
    """Tests for the log configuration section."""

    def test_log_section_exists(self, config):
        assert "log" in config, "config must have a 'log' section"

    def test_log_section_is_dict(self, config):
        assert isinstance(config["log"], dict), "'log' must be a JSON object"

    def test_log_level_exists(self, config):
        assert "level" in config["log"], "'log' section must have 'level' field"

    def test_log_level_is_valid(self, config):
        valid_levels = {"trace", "debug", "info", "warn", "error", "fatal", "panic"}
        level = config["log"]["level"]
        assert level in valid_levels, (
            f"log level '{level}' not in valid levels: {valid_levels}"
        )


class TestConfigInbounds:
    """Tests for inbound proxy configuration."""

    def test_inbounds_exists(self, config):
        assert "inbounds" in config, "config must have 'inbounds' section"

    def test_inbounds_is_list(self, config):
        assert isinstance(config["inbounds"], list), "'inbounds' must be a list"

    def test_inbounds_not_empty(self, config):
        assert len(config["inbounds"]) > 0, "'inbounds' must have at least one entry"

    def test_inbound_has_type(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            assert "type" in inbound, f"inbound[{i}] must have 'type' field"

    def test_inbound_type_is_valid(self, config):
        valid_types = {
            "vless", "vmess", "trojan", "shadowsocks", "naive",
            "hysteria", "hysteria2", "tuic", "mixed", "socks",
            "http", "tun", "redirect", "tproxy",
        }
        for i, inbound in enumerate(config["inbounds"]):
            assert inbound["type"] in valid_types, (
                f"inbound[{i}] type '{inbound['type']}' is not a recognized sing-box type"
            )

    def test_inbound_has_tag(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            assert "tag" in inbound, f"inbound[{i}] must have 'tag' field"

    def test_inbound_tags_unique(self, config):
        tags = [ib["tag"] for ib in config["inbounds"] if "tag" in ib]
        assert len(tags) == len(set(tags)), "inbound tags must be unique"

    def test_inbound_has_listen_port(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            assert "listen_port" in inbound, (
                f"inbound[{i}] must have 'listen_port' field"
            )

    def test_inbound_listen_port_valid_range(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            port = inbound["listen_port"]
            assert isinstance(port, int), f"inbound[{i}] listen_port must be integer"
            assert 1 <= port <= 65535, (
                f"inbound[{i}] listen_port {port} out of valid range (1-65535)"
            )

    def test_inbound_listen_address(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if "listen" in inbound:
                listen = inbound["listen"]
                valid_addresses = {"::", "0.0.0.0", "127.0.0.1", "::1"}
                assert listen in valid_addresses or listen.count(".") == 3, (
                    f"inbound[{i}] listen address '{listen}' looks invalid"
                )


class TestConfigInboundUsers:
    """Tests for user configuration in inbounds."""

    def test_inbound_has_users(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if inbound.get("type") in {"vless", "vmess", "trojan"}:
                assert "users" in inbound, (
                    f"inbound[{i}] of type '{inbound['type']}' must have 'users' field"
                )

    def test_users_is_list(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if "users" in inbound:
                assert isinstance(inbound["users"], list), (
                    f"inbound[{i}] 'users' must be a list"
                )

    def test_users_not_empty(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if "users" in inbound:
                assert len(inbound["users"]) > 0, (
                    f"inbound[{i}] must have at least one user"
                )

    def test_user_has_uuid(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if inbound.get("type") in {"vless", "vmess"}:
                for j, user in enumerate(inbound.get("users", [])):
                    assert "uuid" in user, (
                        f"inbound[{i}].users[{j}] must have 'uuid' field"
                    )

    def test_user_uuid_format(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if inbound.get("type") in {"vless", "vmess"}:
                for j, user in enumerate(inbound.get("users", [])):
                    uuid = user.get("uuid", "")
                    assert UUID_PATTERN.match(uuid), (
                        f"inbound[{i}].users[{j}] uuid '{uuid}' is not valid UUID format"
                    )


class TestConfigInboundTransport:
    """Tests for transport configuration in inbounds."""

    def test_transport_section(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if "transport" in inbound:
                transport = inbound["transport"]
                assert isinstance(transport, dict), (
                    f"inbound[{i}] 'transport' must be a JSON object"
                )

    def test_transport_has_type(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if "transport" in inbound:
                assert "type" in inbound["transport"], (
                    f"inbound[{i}] transport must have 'type' field"
                )

    def test_transport_type_valid(self, config):
        valid_transport_types = {"ws", "http", "grpc", "quic", "httpupgrade"}
        for i, inbound in enumerate(config["inbounds"]):
            if "transport" in inbound:
                t_type = inbound["transport"]["type"]
                assert t_type in valid_transport_types, (
                    f"inbound[{i}] transport type '{t_type}' not recognized"
                )

    def test_ws_transport_has_path(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if "transport" in inbound:
                transport = inbound["transport"]
                if transport.get("type") == "ws":
                    assert "path" in transport, (
                        f"inbound[{i}] WebSocket transport must have 'path' field"
                    )

    def test_ws_path_starts_with_slash(self, config):
        for i, inbound in enumerate(config["inbounds"]):
            if "transport" in inbound:
                transport = inbound["transport"]
                if transport.get("type") == "ws" and "path" in transport:
                    assert transport["path"].startswith("/"), (
                        f"inbound[{i}] WebSocket path must start with '/'"
                    )


class TestConfigOutbounds:
    """Tests for outbound configuration."""

    def test_outbounds_exists(self, config):
        assert "outbounds" in config, "config must have 'outbounds' section"

    def test_outbounds_is_list(self, config):
        assert isinstance(config["outbounds"], list), "'outbounds' must be a list"

    def test_outbounds_not_empty(self, config):
        assert len(config["outbounds"]) > 0, "'outbounds' must have at least one entry"

    def test_outbound_has_type(self, config):
        for i, outbound in enumerate(config["outbounds"]):
            assert "type" in outbound, f"outbound[{i}] must have 'type' field"

    def test_outbound_has_tag(self, config):
        for i, outbound in enumerate(config["outbounds"]):
            assert "tag" in outbound, f"outbound[{i}] must have 'tag' field"

    def test_outbound_tags_unique(self, config):
        tags = [ob["tag"] for ob in config["outbounds"] if "tag" in ob]
        assert len(tags) == len(set(tags)), "outbound tags must be unique"

    def test_outbound_type_valid(self, config):
        valid_types = {
            "direct", "block", "dns", "socks", "http", "shadowsocks",
            "vmess", "vless", "trojan", "hysteria", "hysteria2",
            "wireguard", "tor", "ssh", "tuic", "selector", "urltest",
        }
        for i, outbound in enumerate(config["outbounds"]):
            assert outbound["type"] in valid_types, (
                f"outbound[{i}] type '{outbound['type']}' is not recognized"
            )

    def test_has_direct_outbound(self, config):
        types = [ob["type"] for ob in config["outbounds"]]
        assert "direct" in types, "config should have at least one 'direct' outbound"
