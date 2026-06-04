from pathlib import Path

from agent_pocket_mock_bridge.server import (
    BonjourAdvertisement,
    build_parser as build_server_parser,
    resolve_pairing_advertised_endpoint,
)
from kaka_mobile_runtime_kit.cli import (
    BridgeConfig,
    build_bridge_environment,
    build_server_command,
    doctor_report,
    pairing_url,
    validate_start_config,
)


def test_server_cli_accepts_recipe_local_provider():
    args = build_server_parser().parse_args(["--photo-provider", "recipe_local"])

    assert args.photo_provider == "recipe_local"


def test_bonjour_advertisement_can_publish_runtime_identifier():
    command = BonjourAdvertisement(
        name="Kaka Mobile Bridge",
        host="192.168.1.10",
        port=8765,
        pairing_code="pair_dev",
        runtime="openclaw",
    ).command()

    assert "runtime=openclaw" in command
    assert "endpoint=http://192.168.1.10:8765" in command


def test_server_lan_pairing_endpoint_uses_advertised_host_instead_of_request_host():
    args = build_server_parser().parse_args(
        [
            "--host",
            "0.0.0.0",
            "--bonjour",
            "--bonjour-host",
            "192.168.1.104",
        ]
    )

    endpoint = resolve_pairing_advertised_endpoint(args, 8765)

    assert endpoint == "http://192.168.1.104:8765"


def test_runtime_bridge_default_command_is_loopback_recipe_local():
    command = build_server_command(BridgeConfig())

    assert "--host" in command
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--photo-provider") + 1] == "recipe_local"
    assert command[command.index("--vision-provider") + 1] == "fixture"
    assert "--bonjour" not in command


def test_runtime_bridge_can_route_vision_to_runtime_http_provider():
    command = build_server_command(
        BridgeConfig(
            vision_provider="runtime_http",
            vision_endpoint="http://127.0.0.1:7799/kaka/vision",
        )
    )

    assert command[command.index("--vision-provider") + 1] == "runtime_http"
    assert command[command.index("--vision-endpoint") + 1] == "http://127.0.0.1:7799/kaka/vision"


def test_runtime_bridge_lan_bonjour_command_is_explicit():
    command = build_server_command(
        BridgeConfig(
            lan=True,
            bonjour=True,
            bonjour_host="192.168.1.10",
            runtime="hermes",
            hermes_profile="dev-lead",
        )
    )

    assert command[command.index("--host") + 1] == "0.0.0.0"
    assert "--bonjour" in command
    assert command[command.index("--bonjour-host") + 1] == "192.168.1.10"
    assert command[command.index("--runtime") + 1] == "hermes"
    assert command[command.index("--hermes-profile") + 1] == "dev-lead"


def test_runtime_bridge_rejects_iphone_bonjour_without_reachable_host():
    errors = validate_start_config(BridgeConfig(bonjour=True))

    assert errors == ["Bonjour discovery for iPhone requires --lan or --bonjour-host."]


def test_runtime_bridge_requires_vision_endpoint_for_runtime_http_provider():
    errors = validate_start_config(BridgeConfig(vision_provider="runtime_http"))

    assert errors == ["--vision-endpoint is required when --vision-provider runtime_http."]


def test_runtime_bridge_environment_prepends_mock_bridge_path():
    repo_root = Path("/tmp/kaka")
    env = build_bridge_environment(
        repo_root,
        base_env={"PYTHONPATH": "existing"},
    )

    assert env["PYTHONPATH"].split(":")[0] == str((repo_root / "mock_bridge").resolve())
    assert env["PYTHONPATH"].split(":")[1] == "existing"


def test_pairing_url_points_to_development_qr_page():
    assert pairing_url("192.168.1.10", 8765) == "http://192.168.1.10:8765/mobile/v1/pairing/dev.html"


def test_doctor_report_does_not_print_secret_values():
    report = doctor_report(Path("."), photo_pack_root="photo-pack")
    rendered = str(report)

    assert "sk-" not in rendered
    assert report["checks"]["recipe_local_adapter"]["ok"] is True
