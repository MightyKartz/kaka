import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from kaka_mobile_runtime_kit.host_extension_install_package import (
    build_host_extension_install_package,
    write_host_extension_install_package,
)


FORBIDDEN_USER_COPY = (
    "export HERMES_KAKA_HOST_API",
    "export OPENCLAW_KAKA_HOST_API",
    "--private-adapter-command",
    "write adapter code",
    "paste Runtime Kit command",
)


def test_install_package_handoff_hermes_is_plugin_shape() -> None:
    package = build_host_extension_install_package(runtime="hermes")

    assert package["schema_version"] == "kaka.host_extension_install_package.v1"
    assert package["surface"] == "hermes_openclaw_host_extension_install_package"
    assert package["runtime"] == "hermes"
    assert package["package"]["install_shape"] == "hermes_plugin"
    assert package["package"]["ordinary_user_entrypoint"] == "Hermes Plugin: Kaka Mobile Bridge"
    assert package["adapter_command"]["default_command_name"] == "hermes-kaka-host-api"
    assert package["adapter_command"]["visibility"] == "extension_internal"
    assert package["phone_api"]["base_path"] == "/mobile/v1"
    assert package["phone_api"]["private_host_api_exposed"] is False
    assert package["safety"]["requires_manual_adapter_code"] is False
    assert package["safety"]["requires_environment_variable"] is False
    assert package["safety"]["starts_bridge_on_install"] is False
    assert package["release_gates"]["requires_host_signature"] is True
    assert package["release_gates"]["requires_conformance_report"] is True


def test_install_package_handoff_openclaw_is_skill_shape() -> None:
    package = build_host_extension_install_package(runtime="openclaw")

    assert package["package"]["install_shape"] == "openclaw_skill"
    assert package["package"]["ordinary_user_entrypoint"] == "OpenClaw Skill: Kaka Mobile Bridge"
    assert package["adapter_command"]["default_command_name"] == "openclaw-kaka-host-api"
    assert package["adapter_command"]["environment_variable"] == "OPENCLAW_KAKA_HOST_API"
    generated_paths = {entry["path"] for entry in package["generated_files"]}
    assert "openclaw-skill/SKILL.md" in generated_paths
    assert "openclaw-skill/kaka-mobile-bridge.sidecar.json" in generated_paths


def test_install_package_handoff_rejects_unknown_runtime() -> None:
    with pytest.raises(ValueError, match="Unsupported host extension runtime"):
        build_host_extension_install_package(runtime="sidecar")


def test_install_package_handoff_exposes_p3_19_acceptance_contract() -> None:
    package = build_host_extension_install_package(runtime="hermes")

    generated_paths = {entry["path"] for entry in package["generated_files"]}
    assert "host-ui/acceptance.json" in generated_paths
    assert "release-gates/local-tls-readiness.command.json" in generated_paths
    assert "release-gates/host-shell-pilot-evidence-manifest.command.json" in generated_paths
    assert "release-gates/host-codex-developer-plugin-source.command.json" in generated_paths

    host_ui = package["host_ui"]
    assert host_ui["acceptance"]["initial_state_after_install"] == "installed_disabled"
    assert host_ui["acceptance"]["requires_explicit_enable"] is True
    assert host_ui["acceptance"]["default_bind_mode"] == "loopback"
    assert host_ui["acceptance"]["lan_bonjour_requires_visible_opt_in"] is True
    assert host_ui["acceptance"]["pairing_methods"] == ["short_lived_qr", "bonjour_opt_in"]
    assert "show_tls_readiness" in host_ui["required_actions"]
    assert "repair_port_conflict" in host_ui["required_actions"]
    assert "show_failure_recovery" in host_ui["required_actions"]
    assert "provider_keys" in host_ui["acceptance"]["must_not_expose_to_phone"]
    assert "private_adapter_command_path" in host_ui["acceptance"]["must_not_expose_to_phone"]

    install_drill = package["install_drill"]
    assert install_drill["ordered_steps"] == [
        "install_host_extension",
        "verify_disabled_after_install",
        "enable_bridge",
        "verify_loopback_default",
        "check_tls_readiness",
        "show_short_lived_qr",
        "pair_iphone_mobile_v1",
        "opt_in_bonjour_on_trusted_lan",
        "run_health_check",
        "revoke_and_repair",
        "run_update_drill",
        "run_failure_recovery_drill",
        "open_redacted_logs",
        "uninstall_and_verify_cleanup",
        "archive_release_evidence",
    ]
    assert install_drill["evidence_receipts"] == [
        "install_receipt_ref",
        "update_receipt_ref",
        "failure_recovery_receipt_ref",
        "log_redaction_review_ref",
        "uninstall_receipt_ref",
        "evidence_manifest_ref",
    ]

    release_gates = package["release_gates"]
    assert release_gates["requires_host_ui_acceptance"] is True
    assert release_gates["requires_install_drill_runbook"] is True
    assert release_gates["requires_tls_readiness"] is True
    assert release_gates["requires_host_extension_readiness"] is True
    assert release_gates["requires_codex_developer_plugin_source"] is True


def test_install_package_handoff_exposes_ordinary_user_quickstart() -> None:
    package = build_host_extension_install_package(runtime="hermes")

    generated_paths = {entry["path"] for entry in package["generated_files"]}
    assert "host-ui/user-quickstart.md" in generated_paths
    assert "install-drill/user-journey.json" in generated_paths

    quickstart = package["ordinary_user_quickstart"]
    assert quickstart["surface"] == "host_native_plugin_or_skill"
    assert quickstart["audience"] == "ordinary_user"
    assert quickstart["runtime_label"] == "Hermes"
    assert quickstart["entrypoint"] == "Hermes Plugin: Kaka Mobile Bridge"
    assert quickstart["phone_api_path"] == "/mobile/v1"
    assert quickstart["steps"] == [
        "install_host_extension_from_host_channel",
        "open_kaka_mobile_bridge_panel",
        "verify_installed_disabled",
        "enable_bridge_explicitly",
        "pair_with_short_lived_qr_or_bonjour_opt_in",
        "run_health_check",
    ]
    assert quickstart["never_ask_user_to"] == [
        "write_adapter_code",
        "set_private_adapter_command",
        "export_host_api_environment_variable",
        "paste_runtime_kit_command_chain",
        "install_codex_plugin_or_skill",
    ]

    user_copy = "\n".join(quickstart["user_copy"])
    assert "Install Kaka Mobile Bridge from the Hermes extension channel." in user_copy
    assert "Open Hermes Plugin: Kaka Mobile Bridge." in user_copy
    assert "Enable Kaka Mobile Bridge when you are ready to pair." in user_copy
    assert "Scan the short-lived QR code with Kaka iPhone." in user_copy
    assert "Kaka iPhone connects through /mobile/v1 only." in user_copy
    for forbidden in FORBIDDEN_USER_COPY:
        assert forbidden not in user_copy


def test_install_package_exposes_p3_35_installation_blueprint() -> None:
    package = build_host_extension_install_package(runtime="hermes")

    generated_paths = {entry["path"] for entry in package["generated_files"]}
    assert "host-ui/installation-blueprint.json" in generated_paths

    blueprint = package["installation_blueprint"]
    assert blueprint["schema_version"] == "kaka.host_extension_installation_blueprint.v1"
    assert blueprint["surface"] == "hermes_openclaw_host_extension_installation_blueprint"
    assert blueprint["runtime"] == "hermes"
    assert blueprint["package_manifest"]["install_shape"] == "hermes_plugin"
    assert blueprint["package_manifest"]["ordinary_user_entrypoint"] == (
        "Hermes Plugin: Kaka Mobile Bridge"
    )
    assert blueprint["package_manifest"]["disabled_by_default"] is True
    assert blueprint["host_ui"]["default_state_after_install"] == "installed_disabled"
    assert blueprint["host_ui"]["requires_explicit_enable"] is True
    assert blueprint["host_ui"]["loopback_default"] is True
    assert blueprint["host_ui"]["trusted_lan_requires_visible_opt_in"] is True
    assert "show_qr" in blueprint["host_ui"]["required_controls"]
    assert "show_tls_readiness" in blueprint["host_ui"]["required_controls"]
    assert "revoke_iphone" in blueprint["host_ui"]["required_controls"]
    assert "uninstall_extension" in blueprint["host_ui"]["required_controls"]
    assert "pairing_receipt_ref" in blueprint["lifecycle_receipts"]["required_refs"]
    assert "p3_7_external_install_drill" in blueprint["evidence_gates"]["required_gates"]
    assert blueprint["codex_automation_boundary"]["ordinary_user_installs_codex"] is False
    assert blueprint["codex_automation_boundary"]["writes_user_home"] is False
    assert blueprint["phone_api"]["base_path"] == "/mobile/v1"
    assert blueprint["phone_api"]["private_host_api_exposed"] is False
    assert blueprint["side_effects"]["installs_package"] is False
    assert blueprint["side_effects"]["starts_bridge"] is False
    assert blueprint["side_effects"]["invokes_private_adapter"] is False
    assert blueprint["side_effects"]["writes_codex_user_home"] is False


def test_install_package_installation_blueprint_uses_openclaw_shape() -> None:
    package = build_host_extension_install_package(runtime="openclaw")
    blueprint = package["installation_blueprint"]

    assert blueprint["runtime"] == "openclaw"
    assert blueprint["package_manifest"]["install_shape"] == "openclaw_skill"
    assert blueprint["package_manifest"]["ordinary_user_entrypoint"] == (
        "OpenClaw Skill: Kaka Mobile Bridge"
    )
    assert blueprint["adapter_command"]["default_command_name"] == "openclaw-kaka-host-api"
    assert blueprint["adapter_command"]["visibility"] == "extension_internal"


def test_install_package_handoff_validates_against_schema() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-extension-install-package.schema.json").read_text()
    )

    Draft202012Validator(schema).validate(build_host_extension_install_package(runtime="hermes"))
    Draft202012Validator(schema).validate(build_host_extension_install_package(runtime="openclaw"))


def test_install_package_schema_rejects_user_host_api_drift() -> None:
    schema = json.loads(
        Path("runtime-kit/packaging/host-extension-install-package.schema.json").read_text()
    )
    validator = Draft202012Validator(schema)
    package = json.loads(json.dumps(build_host_extension_install_package(runtime="hermes")))

    manual_code = json.loads(json.dumps(package))
    manual_code["safety"]["requires_manual_adapter_code"] = True
    assert not validator.is_valid(manual_code)

    env_required = json.loads(json.dumps(package))
    env_required["safety"]["requires_environment_variable"] = True
    assert not validator.is_valid(env_required)

    phone_private_api = json.loads(json.dumps(package))
    phone_private_api["phone_api"]["private_host_api_exposed"] = True
    assert not validator.is_valid(phone_private_api)

    visible_adapter = json.loads(json.dumps(package))
    visible_adapter["adapter_command"]["visibility"] = "phone_visible"
    assert not validator.is_valid(visible_adapter)

    auto_start = json.loads(json.dumps(package))
    auto_start["host_ui"]["acceptance"]["initial_state_after_install"] = "running_after_install"
    assert not validator.is_valid(auto_start)

    hidden_enable = json.loads(json.dumps(package))
    hidden_enable["host_ui"]["acceptance"]["requires_explicit_enable"] = False
    assert not validator.is_valid(hidden_enable)

    no_tls_gate = json.loads(json.dumps(package))
    no_tls_gate["release_gates"]["requires_tls_readiness"] = False
    assert not validator.is_valid(no_tls_gate)

    no_codex_source_gate = json.loads(json.dumps(package))
    no_codex_source_gate["release_gates"]["requires_codex_developer_plugin_source"] = False
    assert not validator.is_valid(no_codex_source_gate)

    missing_quickstart = json.loads(json.dumps(package))
    missing_quickstart.pop("ordinary_user_quickstart")
    assert not validator.is_valid(missing_quickstart)

    no_blueprint = json.loads(json.dumps(package))
    no_blueprint.pop("installation_blueprint")
    assert not validator.is_valid(no_blueprint)

    wrong_surface = json.loads(json.dumps(package))
    wrong_surface["ordinary_user_quickstart"]["surface"] = "codex_skill"
    assert not validator.is_valid(wrong_surface)

    phone_private_quickstart = json.loads(json.dumps(package))
    phone_private_quickstart["ordinary_user_quickstart"]["phone_api_path"] = "/host/private"
    assert not validator.is_valid(phone_private_quickstart)

    missing_quickstart_file = json.loads(json.dumps(package))
    missing_quickstart_file["generated_files"] = [
        entry for entry in package["generated_files"]
        if entry["path"] != "host-ui/user-quickstart.md"
    ]
    assert not validator.is_valid(missing_quickstart_file)

    wrong_journey_kind = json.loads(json.dumps(package))
    for entry in wrong_journey_kind["generated_files"]:
        if entry["path"] == "install-drill/user-journey.json":
            entry["kind"] = "install_drill_runbook"
    assert not validator.is_valid(wrong_journey_kind)

    missing_blueprint_file = json.loads(json.dumps(package))
    missing_blueprint_file["generated_files"] = [
        entry for entry in package["generated_files"]
        if entry["path"] != "host-ui/installation-blueprint.json"
    ]
    assert not validator.is_valid(missing_blueprint_file)

    wrong_blueprint_file_kind = json.loads(json.dumps(package))
    for entry in wrong_blueprint_file_kind["generated_files"]:
        if entry["path"] == "host-ui/installation-blueprint.json":
            entry["kind"] = "host_ui_contract"
    assert not validator.is_valid(wrong_blueprint_file_kind)

    auto_enabled_blueprint = json.loads(json.dumps(package))
    auto_enabled_blueprint["installation_blueprint"]["package_manifest"][
        "disabled_by_default"
    ] = False
    assert not validator.is_valid(auto_enabled_blueprint)

    hidden_enable_blueprint = json.loads(json.dumps(package))
    hidden_enable_blueprint["installation_blueprint"]["host_ui"][
        "requires_explicit_enable"
    ] = False
    assert not validator.is_valid(hidden_enable_blueprint)

    missing_p3_7_gate = json.loads(json.dumps(package))
    missing_p3_7_gate["installation_blueprint"]["evidence_gates"][
        "required_gates"
    ].remove("p3_7_external_install_drill")
    assert not validator.is_valid(missing_p3_7_gate)

    public_codex_installer = json.loads(json.dumps(package))
    public_codex_installer["installation_blueprint"]["codex_automation_boundary"][
        "ordinary_user_installs_codex"
    ] = True
    assert not validator.is_valid(public_codex_installer)

    writes_codex_home = json.loads(json.dumps(package))
    writes_codex_home["installation_blueprint"]["side_effects"][
        "writes_codex_user_home"
    ] = True
    assert not validator.is_valid(writes_codex_home)

    for forbidden_copy in (
        "Ask the user to export HERMES_KAKA_HOST_API before pairing.",
        "Configure --private-adapter-command before opening Kaka.",
        "Have the user write adapter code in the terminal.",
        "Install Codex plugin as the public Kaka package.",
        "Connect Kaka iPhone to /host/private.",
    ):
        unsafe_quickstart_copy = json.loads(json.dumps(package))
        unsafe_quickstart_copy["ordinary_user_quickstart"]["user_copy"].append(forbidden_copy)
        assert not validator.is_valid(unsafe_quickstart_copy)


def test_write_install_package_materializes_host_handoff_files(tmp_path: Path) -> None:
    result = write_host_extension_install_package(runtime="openclaw", output_dir=tmp_path)

    root = tmp_path / "kaka-mobile-bridge-openclaw-install-package"
    assert result["written"] is True
    assert result["output_root"] == str(root)
    assert (root / "README.md").exists()
    assert (root / "openclaw-skill" / "SKILL.md").exists()
    assert (root / "openclaw-skill" / "kaka-mobile-bridge.sidecar.json").exists()
    assert (root / "bin" / "openclaw-kaka-host-api.README.md").exists()
    assert (root / "host-ui" / "kaka-mobile-bridge-panel.json").exists()
    assert (root / "host-ui" / "acceptance.json").exists()
    assert (root / "host-ui" / "installation-blueprint.json").exists()
    assert (root / "host-ui" / "user-quickstart.md").exists()
    assert (root / "install-drill" / "runbook.json").exists()
    assert (root / "install-drill" / "user-journey.json").exists()
    assert (root / "release-gates" / "host-extension-readiness.command.json").exists()
    assert (root / "release-gates" / "local-tls-readiness.command.json").exists()
    assert (root / "release-gates" / "host-shell-pilot-evidence-manifest.command.json").exists()
    assert (root / "release-gates" / "host-codex-developer-plugin-source.command.json").exists()

    expected_written_paths = {entry["path"] for entry in result["generated_files"]}
    actual_written_paths = {
        str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()
    }
    assert actual_written_paths == expected_written_paths

    acceptance = json.loads((root / "host-ui" / "acceptance.json").read_text())
    assert acceptance["initial_state_after_install"] == "installed_disabled"
    assert acceptance["requires_explicit_enable"] is True

    blueprint = json.loads((root / "host-ui" / "installation-blueprint.json").read_text())
    assert blueprint["schema_version"] == "kaka.host_extension_installation_blueprint.v1"
    assert blueprint["runtime"] == "openclaw"
    assert blueprint["side_effects"]["writes_codex_user_home"] is False

    quickstart = json.loads((root / "install-drill" / "user-journey.json").read_text())
    assert quickstart["surface"] == "host_native_plugin_or_skill"
    assert quickstart["audience"] == "ordinary_user"
    assert quickstart["phone_api_path"] == "/mobile/v1"
    assert "install_codex_plugin_or_skill" in quickstart["never_ask_user_to"]

    quickstart_markdown = (root / "host-ui" / "user-quickstart.md").read_text()
    assert "Install Kaka Mobile Bridge from the OpenClaw extension channel." in quickstart_markdown
    assert "Kaka iPhone connects through `/mobile/v1` only." in quickstart_markdown
    for forbidden in FORBIDDEN_USER_COPY:
        assert forbidden not in quickstart_markdown

    for command_name in (
        "host-extension-readiness",
        "host-private-adapter-conformance",
        "local-tls-readiness",
        "host-shell-pilot-evidence-manifest",
        "host-codex-developer-plugin-source",
    ):
        command = json.loads(
            (root / "release-gates" / f"{command_name}.command.json").read_text()
        )
        assert command["mutates_host"] is False
        assert command["argv"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            command_name,
            "--runtime",
            "openclaw",
        ]

    ordinary_copy = (
        (root / "README.md").read_text()
        + "\n"
        + (root / "openclaw-skill" / "SKILL.md").read_text()
    )
    for forbidden in FORBIDDEN_USER_COPY:
        assert forbidden not in ordinary_copy


def test_install_package_cli_prints_preview(capsys) -> None:
    from kaka_mobile_runtime_kit.cli import main

    exit_code = main(["host-extension-install-package", "--runtime", "hermes"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["schema_version"] == "kaka.host_extension_install_package.v1"
    assert output["runtime"] == "hermes"
    assert output["written"] is False


def test_install_package_cli_writes_output(tmp_path: Path, capsys) -> None:
    from kaka_mobile_runtime_kit.cli import main

    exit_code = main(
        [
            "host-extension-install-package",
            "--runtime",
            "openclaw",
            "--output-dir",
            str(tmp_path),
            "--write",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["written"] is True
    assert Path(output["output_root"]).name == "kaka-mobile-bridge-openclaw-install-package"
