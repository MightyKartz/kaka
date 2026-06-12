import json

from kaka_mobile_runtime_kit.cli import BridgeConfig, build_runtime_host_package, main
from kaka_mobile_runtime_kit.host_adapter import (
    HOST_ADAPTER_ACTIONS,
    HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS,
)
from kaka_mobile_runtime_kit.host_private_adapter_conformance import REQUIRED_CAPABILITIES
from kaka_mobile_runtime_kit.host_private_adapter_package import (
    build_host_private_adapter_package,
)


def test_private_adapter_package_declares_host_owned_binary_distribution():
    package = build_host_private_adapter_package(
        BridgeConfig(runtime="hermes"),
        distribution_source="signed_download",
        distribution_channel="stable",
        package_version="1.2.3",
        command_name="hermes-kaka-host-api",
    )

    assert package["schema_version"] == "kaka.host_private_adapter_package.v1"
    assert package["surface"] == "hermes_openclaw_host_private_adapter_package"
    assert package["runtime"] == "hermes"
    assert package["binary"] == {
        "owner": "host_shell",
        "repository_owner": "hermes_or_openclaw",
        "private_api_implementation": "not_bundled_in_kaka",
        "default_command_name": "hermes-kaka-host-api",
    }
    assert package["distribution"] == {
        "source": "signed_download",
        "channel": "stable",
        "version": "1.2.3",
        "update_policy": "explicit_user_approved",
        "download_owner": "host_shell",
        "signature_policy": "host_shell_required",
    }
    assert package["required_action_ids"] == list(HOST_ADAPTER_ACTIONS)
    assert package["required_capabilities"] == list(REQUIRED_CAPABILITIES)
    assert package["mobile_bridge"]["phone_api_path"] == "/mobile/v1"
    assert package["mobile_bridge"]["phone_api_unchanged"] is True
    assert package["safety"]["runtime_side_only"] is True
    assert package["safety"]["phone_settings_owner"] is False
    assert package["safety"]["forbidden_phone_safe_fields"] == list(
        HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS
    )


def test_private_adapter_package_declares_discovery_sources_and_conformance_gate():
    package = build_host_private_adapter_package(
        BridgeConfig(runtime="openclaw"),
        distribution_source="host_store",
        distribution_channel="beta",
        package_version="2026.6.6",
        command_name="openclaw-kaka-host-api",
    )

    discovery = package["discovery"]
    assert discovery["config_key"] == "private_adapter_command"
    assert discovery["environment_variable"] == "OPENCLAW_KAKA_HOST_API"
    assert discovery["manifest_entrypoint"] == "host_private_adapter.command"
    assert discovery["well_known_paths"] == [
        "~/Library/Application Support/OpenClaw/Kaka/openclaw-kaka-host-api"
    ]

    validation = package["validation"]
    assert validation["requires_conformance_passed"] is True
    assert validation["report_schema"] == "kaka.host_private_adapter_conformance.v1"
    assert validation["conformance_command"] == [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        "host-private-adapter-conformance",
        "--runtime",
        "openclaw",
        "--private-adapter-command",
        "<host-owned-private-adapter-command>",
    ]


def test_host_package_preview_embeds_private_adapter_package_contract():
    package = build_runtime_host_package(
        BridgeConfig(runtime="hermes"),
        distribution_source="enterprise_distribution",
        distribution_channel="managed",
        package_version="5.0.0",
    )

    private_package = package["private_adapter_package"]
    assert private_package["runtime"] == "hermes"
    assert private_package["distribution"]["source"] == "enterprise_distribution"
    assert private_package["distribution"]["channel"] == "managed"
    assert private_package["distribution"]["version"] == "5.0.0"
    assert private_package["binary"]["default_command_name"] == "hermes-kaka-host-api"
    assert private_package["validation"]["requires_conformance_passed"] is True


def test_host_package_preview_cli_outputs_private_adapter_package(capsys):
    exit_code = main([
        "host-package-preview",
        "--runtime",
        "openclaw",
        "--distribution-source",
        "signed_download",
        "--distribution-channel",
        "stable",
        "--package-version",
        "2.3.4",
    ])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["private_adapter_package"]["runtime"] == "openclaw"
    assert output["private_adapter_package"]["binary"]["default_command_name"] == (
        "openclaw-kaka-host-api"
    )
    assert output["private_adapter_package"]["mobile_bridge"]["phone_api_path"] == "/mobile/v1"
