import json
from pathlib import Path

from jsonschema import Draft202012Validator, Draft7Validator

from kaka_mobile_runtime_kit.cli import (
    BridgeConfig,
    build_runtime_host_package,
    build_runtime_settings_preview,
)


PACKAGING_DIR = Path("runtime-kit/packaging")


PROCESS_CONTROLS = (
    "install_runtime_package",
    "update_runtime_package",
    "uninstall_runtime_package",
    "open_runtime_logs",
    "run_health_check",
    "repair_port_conflict",
)

PROCESS_ACTIONS = (
    "install_runtime_package",
    "enable_start_with_runtime",
    "disable_start_with_runtime",
    "update_runtime_package",
    "uninstall_runtime_package",
    "open_runtime_logs",
    "run_health_check",
    "repair_port_conflict",
)

HOST_PACKAGE_ACTIONS = (
    "install_runtime_package",
    "enable_start_with_runtime",
    "disable_start_with_runtime",
    "update_runtime_package",
    "uninstall_runtime_package",
    "open_runtime_logs",
    "run_health_check",
    "repair_port_conflict",
    "supervise_bridge",
)

HOST_ADAPTER_ACTIONS = HOST_PACKAGE_ACTIONS

HOST_PRIVATE_ADAPTER_CAPABILITIES = (
    "distribution",
    "install",
    "login_item",
    "update",
    "uninstall",
    "logs",
    "health",
    "port_repair",
    "supervision",
)


def test_host_package_preview_declares_private_adapter_package_schema():
    host_package_schema = json.loads((PACKAGING_DIR / "host-package.schema.json").read_text())
    private_adapter_schema = json.loads(
        (PACKAGING_DIR / "host-private-adapter-package.schema.json").read_text()
    )
    package = build_runtime_host_package(
        BridgeConfig(runtime="hermes"),
        distribution_source="signed_download",
        distribution_channel="stable",
        package_version="1.2.3",
    )

    Draft7Validator(host_package_schema).validate(package)
    Draft202012Validator(private_adapter_schema).validate(package["private_adapter_package"])

    partial_private_package = json.loads(json.dumps(package["private_adapter_package"]))
    partial_private_package["required_action_ids"] = ["run_health_check"]
    partial_private_package["required_capabilities"] = ["health"]
    assert not Draft202012Validator(private_adapter_schema).is_valid(partial_private_package)

    partial_host_package = json.loads(json.dumps(package))
    partial_host_package["private_adapter_package"] = partial_private_package
    assert not Draft7Validator(host_package_schema).is_valid(partial_host_package)


def test_static_manifests_declare_private_adapter_package_contract():
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    manifests = [
        (
            "hermes",
            json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text()),
        ),
        (
            "openclaw",
            json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text()),
        ),
    ]

    for runtime, manifest in manifests:
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_private_adapter_package"] == {
            "source": "host_package.private_adapter_package",
            "schema_version": "kaka.host_private_adapter_package.v1",
            "runtime_side_only": True,
            "binary_owner": "host_shell",
            "distribution_owner": runtime,
            "requires_conformance_passed": True,
            "phone_api_path": "/mobile/v1",
        }


def test_host_extension_preview_schema_and_manifests_are_declared():
    extension_path = PACKAGING_DIR / "host-extension-preview.schema.json"

    assert extension_path.exists()

    extension_schema = json.loads(extension_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert extension_schema["additionalProperties"] is False
    assert extension_schema["properties"]["schema_version"]["const"] == "kaka.host_extension_preview.v1"
    assert extension_schema["properties"]["surface"]["const"] == "hermes_openclaw_host_extension_preview"
    assert extension_schema["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert extension_schema["properties"]["ordinary_user_install"]["additionalProperties"] is False
    assert (
        extension_schema["properties"]["ordinary_user_install"]["properties"][
            "requires_manual_adapter_code"
        ]["const"]
        is False
    )
    assert (
        extension_schema["properties"]["ordinary_user_install"]["properties"][
            "requires_environment_variable"
        ]["const"]
        is False
    )
    assert extension_schema["properties"]["adapter_command"]["additionalProperties"] is False
    assert extension_schema["properties"]["adapter_command"]["properties"]["visibility"]["const"] == "extension_internal"
    assert (
        extension_schema["properties"]["adapter_command"]["properties"]["developer_fallback_only"]["const"]
        is True
    )
    assert extension_schema["properties"]["adapter_command"]["properties"]["well_known_paths"]["uniqueItems"] is True
    assert extension_schema["properties"]["phone_api"]["properties"]["base_path"]["const"] == "/mobile/v1"
    assert (
        extension_schema["properties"]["phone_api"]["properties"]["private_host_api_exposed"]["const"]
        is False
    )
    assert (
        extension_schema["properties"]["release_gates"]["properties"]["requires_p3_2_conformance"][
            "const"
        ]
        is True
    )
    assert (
        extension_schema["properties"]["release_gates"]["properties"][
            "requires_p3_4_external_pilot_evidence"
        ]["const"]
        is True
    )

    assert "host_extension_preview" in manifest_schema["required"]
    assert "host_extension_preview" in manifest_schema["properties"]
    manifest_without_extension = json.loads(json.dumps(hermes))
    del manifest_without_extension["host_extension_preview"]
    assert not Draft202012Validator(manifest_schema).is_valid(manifest_without_extension)

    for manifest in (hermes, openclaw):
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_extension_preview"] == {
            "source": "host-extension-preview",
            "schema_version": "kaka.host_extension_preview.v1",
            "ordinary_user_install": True,
            "install_shape": f"{manifest['runtime']}_plugin" if manifest["runtime"] == "hermes" else "openclaw_skill",
            "extension_package_owner": "host_shell",
            "manual_adapter_code_required": False,
            "environment_variable_required": False,
            "adapter_command_visibility": "extension_internal",
            "ordinary_user_source": "extension_internal_bundle",
            "developer_fallback_source": "explicit_command_or_env",
            "pairing_ux": "host_ui_qr_or_bonjour",
            "requires_p3_2_conformance": True,
            "requires_p3_4_external_pilot_evidence": True,
            "phone_api_unchanged": True,
        }
        assert manifest["entrypoints"]["host_extension_preview"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-extension-preview",
            "--runtime",
            manifest["runtime"],
        ]


def test_host_extension_preview_schema_rejects_runtime_mismatched_payloads():
    from kaka_mobile_runtime_kit.host_adapter import HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS
    from kaka_mobile_runtime_kit.host_extension_preview import build_host_extension_preview

    schema = json.loads((PACKAGING_DIR / "host-extension-preview.schema.json").read_text())
    validator = Draft202012Validator(schema)

    hermes = json.loads(json.dumps(build_host_extension_preview(runtime="hermes")))
    validator.validate(hermes)

    mismatched_shape = json.loads(json.dumps(hermes))
    mismatched_shape["ordinary_user_install"]["install_shape"] = "openclaw_skill"
    assert not validator.is_valid(mismatched_shape)

    mismatched_command = json.loads(json.dumps(hermes))
    mismatched_command["adapter_command"]["default_command_name"] = "openclaw-kaka-host-api"
    assert not validator.is_valid(mismatched_command)

    mismatched_env = json.loads(json.dumps(hermes))
    mismatched_env["adapter_command"]["environment_variable"] = "OPENCLAW_KAKA_HOST_API"
    assert not validator.is_valid(mismatched_env)

    mismatched_path = json.loads(json.dumps(hermes))
    mismatched_path["adapter_command"]["well_known_paths"] = [
        "~/Library/Application Support/OpenClaw/Kaka/openclaw-kaka-host-api"
    ]
    assert not validator.is_valid(mismatched_path)

    duplicated_forbidden_fields = json.loads(json.dumps(hermes))
    duplicated_forbidden_fields["safety"]["forbidden_phone_safe_fields"] = [
        *HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS,
        HOST_ADAPTER_FORBIDDEN_PHONE_SAFE_FIELDS[0],
    ]
    assert not validator.is_valid(duplicated_forbidden_fields)


def test_runtime_shell_manifest_schema_rejects_host_extension_entrypoint_runtime_mismatch():
    schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    validator = Draft202012Validator(schema)
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())

    validator.validate(hermes)

    wrong_entrypoint = json.loads(json.dumps(hermes))
    wrong_entrypoint["entrypoints"]["host_extension_preview"] = [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        "host-extension-preview",
        "--runtime",
        "openclaw",
    ]
    assert not validator.is_valid(wrong_entrypoint)

    empty_entrypoint = json.loads(json.dumps(hermes))
    empty_entrypoint["entrypoints"]["host_extension_preview"] = []
    assert not validator.is_valid(empty_entrypoint)

    wrong_distribution_owner = json.loads(json.dumps(hermes))
    wrong_distribution_owner["host_private_adapter_package"]["distribution_owner"] = "openclaw"
    assert not validator.is_valid(wrong_distribution_owner)

    wrong_install_shape = json.loads(json.dumps(hermes))
    wrong_install_shape["host_extension_preview"]["install_shape"] = "openclaw_skill"
    assert not validator.is_valid(wrong_install_shape)


def test_host_extension_readiness_schema_and_manifests_are_declared():
    readiness_schema = json.loads((PACKAGING_DIR / "host-extension-readiness.schema.json").read_text())
    shell_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes_manifest = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw_manifest = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert readiness_schema["properties"]["schema_version"]["const"] == "kaka.host_extension_readiness.v1"
    assert "host_extension_readiness" in shell_schema["required"]
    assert "host_extension_readiness" in shell_schema["properties"]
    assert "host_extension_readiness" in shell_schema["properties"]["entrypoints"]["required"]

    expected_common = {
        "source": "host-extension-readiness",
        "schema_version": "kaka.host_extension_readiness.v1",
        "ordinary_user_install": True,
        "manual_adapter_code_required": False,
        "environment_variable_required": False,
        "adapter_command_visibility": "extension_internal",
        "phone_api_unchanged": True,
    }
    assert hermes_manifest["host_extension_readiness"] == expected_common
    assert openclaw_manifest["host_extension_readiness"] == expected_common
    assert hermes_manifest["entrypoints"]["host_extension_readiness"] == [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        "host-extension-readiness",
        "--runtime",
        "hermes",
    ]
    assert openclaw_manifest["entrypoints"]["host_extension_readiness"] == [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        "host-extension-readiness",
        "--runtime",
        "openclaw",
    ]


def test_host_extension_material_intake_schemas_are_packaged_and_closed():
    materials_schema = json.loads(
        (PACKAGING_DIR / "host-extension-materials.schema.json").read_text()
    )
    intake_schema = json.loads(
        (PACKAGING_DIR / "host-extension-material-intake.schema.json").read_text()
    )
    packaging_doc = (PACKAGING_DIR / "PACKAGING.md").read_text()

    Draft202012Validator.check_schema(materials_schema)
    Draft202012Validator.check_schema(intake_schema)
    assert materials_schema["additionalProperties"] is False
    assert intake_schema["additionalProperties"] is False
    assert materials_schema["properties"]["schema_version"]["const"] == (
        "kaka.host_extension_materials.v1"
    )
    assert intake_schema["properties"]["schema_version"]["const"] == (
        "kaka.host_extension_material_intake.v1"
    )
    assert intake_schema["properties"]["surface"]["const"] == (
        "hermes_openclaw_host_extension_material_intake"
    )
    assert intake_schema["properties"]["phone_api"]["properties"]["base_path"]["const"] == "/mobile/v1"
    assert (
        intake_schema["properties"]["phone_api"]["properties"]["phone_api_unchanged"]["const"]
        is True
    )
    assert (
        intake_schema["properties"]["safety"]["properties"]["does_not_install_package"]["const"]
        is True
    )
    assert (
        intake_schema["properties"]["safety"]["properties"]["does_not_fetch_refs"]["const"]
        is True
    )
    assert (
        intake_schema["properties"]["safety"]["properties"]["does_not_invoke_private_adapter"][
            "const"
        ]
        is True
    )
    assert "host-extension-materials.schema.json" in packaging_doc
    assert "host-extension-material-intake.schema.json" in packaging_doc


def test_host_extension_starter_kit_schema_and_manifests_are_declared():
    starter_schema = json.loads((PACKAGING_DIR / "host-extension-starter-kit.schema.json").read_text())
    shell_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    validator = Draft202012Validator(shell_schema)
    hermes_manifest = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw_manifest = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert starter_schema["properties"]["schema_version"]["const"] == "kaka.host_extension_starter_kit.v1"
    assert starter_schema["properties"]["surface"]["const"] == "hermes_openclaw_host_extension_starter_kit"
    assert starter_schema["properties"]["phone_api"]["additionalProperties"] is False
    assert (
        starter_schema["properties"]["adapter_command"]["properties"][
            "starter_kit_contains_proprietary_implementation"
        ]["const"]
        is False
    )
    assert "host_extension_starter_kit" in shell_schema["required"]
    assert "host_extension_starter_kit" in shell_schema["properties"]
    assert "host_extension_starter_kit" in shell_schema["properties"]["entrypoints"]["required"]

    expected_common = {
        "source": "host-extension-starter-kit",
        "schema_version": "kaka.host_extension_starter_kit.v1",
        "ordinary_user_install": True,
        "manual_adapter_code_required": False,
        "environment_variable_required": False,
        "adapter_command_visibility": "extension_internal",
        "starter_kit_contains_proprietary_implementation": False,
        "final_distribution_requires_host_signature": True,
        "phone_api_unchanged": True,
        "non_mutating": True,
        "does_not_install_package": True,
        "does_not_invoke_private_adapter": True,
    }

    for manifest in (hermes_manifest, openclaw_manifest):
        validator.validate(manifest)
        install_shape = "hermes_plugin" if manifest["runtime"] == "hermes" else "openclaw_skill"
        assert manifest["host_extension_starter_kit"] == {
            **expected_common,
            "install_shape": install_shape,
        }
        assert manifest["entrypoints"]["host_extension_starter_kit"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-extension-starter-kit",
            "--runtime",
            manifest["runtime"],
        ]

    manifest_without_starter = json.loads(json.dumps(hermes_manifest))
    del manifest_without_starter["host_extension_starter_kit"]
    assert not validator.is_valid(manifest_without_starter)

    wrong_entrypoint = json.loads(json.dumps(hermes_manifest))
    wrong_entrypoint["entrypoints"]["host_extension_starter_kit"] = [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        "host-extension-starter-kit",
        "--runtime",
        "openclaw",
    ]
    assert not validator.is_valid(wrong_entrypoint)

    empty_entrypoint = json.loads(json.dumps(hermes_manifest))
    empty_entrypoint["entrypoints"]["host_extension_starter_kit"] = []
    assert not validator.is_valid(empty_entrypoint)

    visible_adapter = json.loads(json.dumps(hermes_manifest))
    visible_adapter["host_extension_starter_kit"]["adapter_command_visibility"] = "phone_visible"
    assert not validator.is_valid(visible_adapter)


def test_host_extension_install_package_schema_and_manifests_are_declared():
    install_schema = json.loads(
        (PACKAGING_DIR / "host-extension-install-package.schema.json").read_text()
    )
    shell_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    validator = Draft202012Validator(shell_schema)
    hermes_manifest = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw_manifest = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert install_schema["properties"]["schema_version"]["const"] == (
        "kaka.host_extension_install_package.v1"
    )
    assert install_schema["properties"]["surface"]["const"] == (
        "hermes_openclaw_host_extension_install_package"
    )
    assert "ordinary_user_quickstart" in install_schema["required"]
    quickstart_schema = install_schema["properties"]["ordinary_user_quickstart"]
    assert quickstart_schema["properties"]["surface"]["const"] == "host_native_plugin_or_skill"
    assert quickstart_schema["properties"]["audience"]["const"] == "ordinary_user"
    assert quickstart_schema["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert "installation_blueprint" in install_schema["required"]
    blueprint_schema = install_schema["properties"]["installation_blueprint"]
    assert blueprint_schema["properties"]["schema_version"]["const"] == (
        "kaka.host_extension_installation_blueprint.v1"
    )
    assert blueprint_schema["properties"]["surface"]["const"] == (
        "hermes_openclaw_host_extension_installation_blueprint"
    )
    generated_file_requirements = install_schema["properties"]["generated_files"]["allOf"]
    required_generated_paths = {
        entry["contains"]["properties"]["path"]["const"]
        for entry in generated_file_requirements
    }
    assert "host-ui/user-quickstart.md" in required_generated_paths
    assert "host-ui/installation-blueprint.json" in required_generated_paths
    assert "install-drill/user-journey.json" in required_generated_paths
    assert "host_extension_install_package" in shell_schema["required"]
    assert "host_extension_install_package" in shell_schema["properties"]
    assert "host_extension_install_package" in shell_schema["properties"]["entrypoints"]["required"]

    expected_common = {
        "source": "host-extension-install-package",
        "schema_version": "kaka.host_extension_install_package.v1",
        "surface": "hermes_openclaw_host_extension_install_package",
        "ordinary_user_install": True,
        "manual_adapter_code_required": False,
        "environment_variable_required": False,
        "adapter_command_visibility": "extension_internal",
        "handoff_contains_proprietary_implementation": False,
        "final_distribution_requires_host_signature": True,
        "phone_api_unchanged": True,
        "non_mutating": True,
        "does_not_install_package": True,
        "does_not_invoke_private_adapter": True,
        "requires_host_ui_acceptance": True,
        "requires_install_drill_runbook": True,
        "requires_tls_readiness": True,
        "requires_codex_developer_plugin_source": True,
    }

    for manifest in (hermes_manifest, openclaw_manifest):
        validator.validate(manifest)
        install_shape = "hermes_plugin" if manifest["runtime"] == "hermes" else "openclaw_skill"
        assert manifest["host_extension_install_package"] == {
            **expected_common,
            "install_shape": install_shape,
        }
        assert manifest["entrypoints"]["host_extension_install_package"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-extension-install-package",
            "--runtime",
            manifest["runtime"],
        ]

    manifest_without_package = json.loads(json.dumps(hermes_manifest))
    del manifest_without_package["host_extension_install_package"]
    assert not validator.is_valid(manifest_without_package)

    wrong_entrypoint = json.loads(json.dumps(hermes_manifest))
    wrong_entrypoint["entrypoints"]["host_extension_install_package"] = [
        "python3",
        "-m",
        "kaka_mobile_runtime_kit",
        "host-extension-install-package",
        "--runtime",
        "openclaw",
    ]
    assert not validator.is_valid(wrong_entrypoint)

    visible_adapter = json.loads(json.dumps(hermes_manifest))
    visible_adapter["host_extension_install_package"]["adapter_command_visibility"] = "phone_visible"
    assert not validator.is_valid(visible_adapter)

    no_tls_gate = json.loads(json.dumps(hermes_manifest))
    no_tls_gate["host_extension_install_package"]["requires_tls_readiness"] = False
    assert not validator.is_valid(no_tls_gate)

    codex_as_user_installer = json.loads(json.dumps(hermes_manifest))
    codex_as_user_installer["host_extension_install_package"][
        "requires_codex_developer_plugin_source"
    ] = False
    assert not validator.is_valid(codex_as_user_installer)


def test_host_plugin_skill_devkit_schema_and_manifests_are_declared():
    devkit_schema = json.loads((PACKAGING_DIR / "host-plugin-skill-devkit.schema.json").read_text())
    shell_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    validator = Draft202012Validator(shell_schema)
    hermes_manifest = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw_manifest = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    Draft202012Validator.check_schema(devkit_schema)
    assert devkit_schema["properties"]["schema_version"]["const"] == (
        "kaka.host_plugin_skill_devkit.v1"
    )
    assert devkit_schema["properties"]["surface"]["const"] == (
        "hermes_openclaw_host_plugin_skill_devkit"
    )

    assert "host_plugin_skill_devkit" in shell_schema["required"]
    assert "host_plugin_skill_devkit" in shell_schema["properties"]
    assert "host_plugin_skill_devkit" in shell_schema["properties"]["entrypoints"]["required"]

    expected_common = {
        "source": "host-plugin-skill-devkit",
        "schema_version": "kaka.host_plugin_skill_devkit.v1",
        "surface": "hermes_openclaw_host_plugin_skill_devkit",
        "developer_kit_only": True,
        "ordinary_user_install": False,
        "runtime_side_only": True,
        "non_mutating": True,
        "manual_adapter_code_required": False,
        "environment_variable_required": False,
        "adapter_command_visibility": "extension_internal",
        "contains_proprietary_implementation": False,
        "codex_automation_user_install_surface": False,
        "does_not_install_package": True,
        "does_not_sign_package": True,
        "does_not_publish_package": True,
        "does_not_invoke_private_adapter": True,
        "does_not_run_conformance": True,
        "phone_api_path": "/mobile/v1",
        "private_host_api_exposed": False,
        "phone_api_unchanged": True,
        "final_distribution_requires_host_signature": True,
        "requires_conformance_report": True,
        "requires_evidence_manifest": True,
        "can_mark_p3_4_complete": False,
    }

    for manifest in (hermes_manifest, openclaw_manifest):
        validator.validate(manifest)
        install_shape = "hermes_plugin" if manifest["runtime"] == "hermes" else "openclaw_skill"
        assert manifest["host_plugin_skill_devkit"] == {
            **expected_common,
            "install_shape": install_shape,
        }
        assert manifest["entrypoints"]["host_plugin_skill_devkit"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-plugin-skill-devkit",
            "--runtime",
            manifest["runtime"],
        ]

    visible_adapter = json.loads(json.dumps(hermes_manifest))
    visible_adapter["host_plugin_skill_devkit"]["adapter_command_visibility"] = "phone_visible"
    assert not validator.is_valid(visible_adapter)

    codex_user_surface = json.loads(json.dumps(hermes_manifest))
    codex_user_surface["host_plugin_skill_devkit"]["codex_automation_user_install_surface"] = True
    assert not validator.is_valid(codex_user_surface)


def test_host_codex_developer_plugin_source_schema_and_manifests_are_declared():
    source_schema = json.loads((PACKAGING_DIR / "host-codex-developer-plugin-source.schema.json").read_text())
    shell_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    validator = Draft202012Validator(shell_schema)
    hermes_manifest = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw_manifest = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    Draft202012Validator.check_schema(source_schema)
    assert source_schema["properties"]["schema_version"]["const"] == (
        "kaka.host_codex_developer_plugin_source.v1"
    )
    assert source_schema["properties"]["surface"]["const"] == (
        "hermes_openclaw_host_codex_developer_plugin_source"
    )

    assert "host_codex_developer_plugin_source" in shell_schema["required"]
    assert "host_codex_developer_plugin_source" in shell_schema["properties"]
    assert "host_codex_developer_plugin_source" in shell_schema["properties"]["entrypoints"]["required"]

    expected_common = {
        "source": "host-codex-developer-plugin-source",
        "schema_version": "kaka.host_codex_developer_plugin_source.v1",
        "surface": "hermes_openclaw_host_codex_developer_plugin_source",
        "developer_only": True,
        "ordinary_user_install": False,
        "source_scope": "explicit_output_dir",
        "updates_marketplace": False,
        "writes_user_home": False,
        "installs_codex_plugin": False,
        "phone_api_path": "/mobile/v1",
        "private_host_api_exposed": False,
        "phone_api_unchanged": True,
        "does_not_install_package": True,
        "does_not_start_bridge": True,
        "does_not_invoke_private_adapter": True,
        "does_not_run_conformance": True,
    }

    for manifest in (hermes_manifest, openclaw_manifest):
        validator.validate(manifest)
        install_shape = "hermes_plugin" if manifest["runtime"] == "hermes" else "openclaw_skill"
        plugin_name = f"kaka-host-extension-developer-{manifest['runtime']}"
        assert manifest["host_codex_developer_plugin_source"] == {
            **expected_common,
            "install_shape": install_shape,
            "plugin_name": plugin_name,
        }
        assert manifest["entrypoints"]["host_codex_developer_plugin_source"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-codex-developer-plugin-source",
            "--runtime",
            manifest["runtime"],
        ]

    updates_marketplace = json.loads(json.dumps(hermes_manifest))
    updates_marketplace["host_codex_developer_plugin_source"]["updates_marketplace"] = True
    assert not validator.is_valid(updates_marketplace)

    user_home = json.loads(json.dumps(hermes_manifest))
    user_home["host_codex_developer_plugin_source"]["writes_user_home"] = True
    assert not validator.is_valid(user_home)

    ordinary_user = json.loads(json.dumps(hermes_manifest))
    ordinary_user["host_codex_developer_plugin_source"]["ordinary_user_install"] = True
    assert not validator.is_valid(ordinary_user)

    phone_api = json.loads(json.dumps(hermes_manifest))
    phone_api["host_codex_developer_plugin_source"]["phone_api_unchanged"] = False
    assert not validator.is_valid(phone_api)


def test_host_adapter_action_result_schema_freezes_runtime_side_binding_contract():
    schema = json.loads((PACKAGING_DIR / "host-adapter-action-result.schema.json").read_text())

    assert schema["properties"]["schema_version"]["const"] == "kaka.host_adapter_action_result.v1"
    assert schema["properties"]["surface"]["const"] == "hermes_openclaw_host_adapter_binding"
    assert schema["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert schema["properties"]["adapter_mode"]["enum"] == ["mock", "private"]
    assert schema["properties"]["adapter"]["enum"] == [
        "host_native_install",
        "host_native_enable_login_item",
        "host_native_disable_login_item",
        "host_native_update",
        "host_native_uninstall",
        "host_native_open_logs",
        "host_native_health_check",
        "host_native_repair_port",
        "host_native_supervisor",
    ]
    assert schema["properties"]["runtime_side_only"]["const"] is True
    assert schema["properties"]["state"]["additionalProperties"] is False
    assert schema["properties"]["safety"]["properties"]["phone_api_unchanged"]["const"] is True
    assert schema["properties"]["safety"]["properties"]["runtime_side_only"]["const"] is True
    assert schema["properties"]["safety"]["properties"]["phone_settings_owner"]["const"] is False
    assert schema["properties"]["safety"]["properties"]["no_autostart_on_install"]["const"] is True
    assert (
        schema["properties"]["safety"]["properties"]["no_login_item_creation_by_runtime_kit"]["const"]
        is True
    )
    assert schema["properties"]["safety"]["properties"]["private_host_api_called"]["type"] == "boolean"
    forbidden_requirements = schema["properties"]["safety"]["properties"]["forbidden_phone_safe_fields"][
        "allOf"
    ]
    for field in (
        "runtime_store_path",
        "recall_search_endpoint",
        "provider_keys",
        "auth_env_files",
        "mobile_tokens",
        "tls_private_key_paths",
        "hidden_prompt",
        "hidden_prompts",
        "raw_embeddings",
        "index_rows",
        "task_logs",
        "raw_provider_responses",
        "process_ids",
        "host_log_paths",
    ):
        assert {"contains": {"const": field}} in forbidden_requirements
    assert schema["properties"]["detail"]["additionalProperties"] is False
    assert schema["properties"]["detail"]["properties"]["url"]["maxLength"] == 2048
    assert schema["properties"]["detail"]["properties"]["target"]["maxLength"] == 64
    assert schema["properties"]["detail"]["properties"]["host_api_level"]["maxLength"] == 64
    assert schema["properties"]["detail"]["properties"]["private_api_called"]["type"] == "boolean"
    assert schema["properties"]["detail"]["properties"]["private_api_provider"]["maxLength"] == 64
    assert schema["properties"]["error"]["additionalProperties"] is False
    assert schema["properties"]["error"]["properties"]["message"]["maxLength"] == 256
    error_codes = schema["properties"]["error"]["properties"]["code"]["enum"]
    assert "host_adapter_action_disabled" in error_codes
    assert "private_host_adapter_command_failed" in error_codes
    assert "private_host_adapter_invalid_response" in error_codes
    assert "private_host_adapter_timeout" in error_codes
    assert "unknown_host_adapter_action" not in error_codes
    assert "unsupported_host_adapter_mode" not in error_codes


def test_host_private_adapter_schemas_define_runtime_side_command_contract():
    request = json.loads((PACKAGING_DIR / "host-private-adapter-request.schema.json").read_text())
    response = json.loads((PACKAGING_DIR / "host-private-adapter-response.schema.json").read_text())

    assert request["properties"]["schema_version"]["const"] == "kaka.host_private_adapter_request.v1"
    assert request["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert request["properties"]["runtime_side_only"]["const"] is True
    assert request["properties"]["state"]["additionalProperties"] is False
    assert request["properties"]["host_action"]["additionalProperties"] is False
    assert "runtime_store_path" in [
        item["contains"]["const"]
        for item in request["properties"]["forbidden_phone_safe_fields"]["allOf"]
    ]

    assert response["properties"]["schema_version"]["const"] == "kaka.host_private_adapter_response.v1"
    assert response["properties"]["state"]["additionalProperties"] is False
    assert response["properties"]["detail"]["additionalProperties"] is False
    assert response["properties"]["detail"]["properties"]["private_api_called"]["type"] == "boolean"


def test_host_private_adapter_examples_validate_against_schemas():
    examples_dir = PACKAGING_DIR / "examples"
    private_adapter_request_schema = json.loads(
        (PACKAGING_DIR / "host-private-adapter-request.schema.json").read_text()
    )
    response_schema = json.loads((PACKAGING_DIR / "host-private-adapter-response.schema.json").read_text())
    pilot_schema = json.loads((PACKAGING_DIR / "host-shell-pilot-receipt.schema.json").read_text())
    handoff_schema = json.loads((PACKAGING_DIR / "host-shell-pilot-handoff.schema.json").read_text())
    preflight_schema = json.loads((PACKAGING_DIR / "host-shell-pilot-preflight.schema.json").read_text())
    runbook_schema = json.loads((PACKAGING_DIR / "host-shell-pilot-runbook.schema.json").read_text())
    pilot_request_schema = json.loads((PACKAGING_DIR / "host-shell-pilot-request.schema.json").read_text())
    artifact_review_schema = json.loads(
        (PACKAGING_DIR / "host-shell-pilot-artifact-review.schema.json").read_text()
    )
    evidence_manifest_schema = json.loads(
        (PACKAGING_DIR / "host-shell-pilot-evidence-manifest.schema.json").read_text()
    )

    request_examples = (
        "run_health_check.request.json",
        "install_approved.request.json",
    )
    response_examples = (
        "run_health_check.response.json",
        "install_approved.response.json",
        "host_error.response.json",
    )

    for filename in request_examples:
        request_example = json.loads((examples_dir / filename).read_text())
        Draft7Validator(private_adapter_request_schema).validate(request_example)

    health_request = json.loads((examples_dir / "run_health_check.request.json").read_text())
    assert health_request["action_id"] == "run_health_check"
    assert health_request["adapter"] == "host_native_health_check"
    assert health_request["approved"] is False
    assert health_request["host_action"]["mutates_host_state"] is False
    assert health_request["host_action"]["requires_explicit_user_approval"] is False

    install_request = json.loads((examples_dir / "install_approved.request.json").read_text())
    assert install_request["action_id"] == "install_runtime_package"
    assert install_request["adapter"] == "host_native_install"
    assert install_request["approved"] is True
    assert install_request["host_action"]["mutates_host_state"] is True
    assert install_request["host_action"]["requires_explicit_user_approval"] is True

    for filename in response_examples:
        Draft7Validator(response_schema).validate(
            json.loads((examples_dir / filename).read_text())
        )

    invalid_response = json.loads(
        (examples_dir / "invalid_extra_field.response.json").read_text()
    )
    assert not Draft7Validator(response_schema).is_valid(invalid_response)

    pilot_ready = json.loads((examples_dir / "pilot_ready.receipt.json").read_text())
    Draft202012Validator(pilot_schema).validate(pilot_ready)
    assert pilot_ready["status"] == "ready"
    assert pilot_ready["private_adapter_command"]["source"] == "argument"
    assert pilot_ready["release_readiness"]["can_mark_p3_4_complete"] is True

    pilot_handoff_blocked = json.loads((examples_dir / "pilot_handoff.blocked.json").read_text())
    Draft202012Validator(handoff_schema).validate(pilot_handoff_blocked)
    Draft202012Validator(pilot_schema).validate(pilot_handoff_blocked["pilot_receipt"])
    assert pilot_handoff_blocked["handoff_status"] == "incomplete"
    assert pilot_handoff_blocked["p3_4_complete"] is False
    assert pilot_handoff_blocked["audit_refs"]["complete"] is False

    pilot_preflight_blocked = json.loads((examples_dir / "pilot_preflight.blocked.json").read_text())
    Draft202012Validator(preflight_schema).validate(pilot_preflight_blocked)
    assert pilot_preflight_blocked["status"] == "blocked"
    assert pilot_preflight_blocked["p3_4_complete"] is False
    assert pilot_preflight_blocked["safety"]["does_not_invoke_private_adapter_command"] is True

    pilot_runbook_blocked = json.loads((examples_dir / "pilot_runbook.blocked.json").read_text())
    Draft202012Validator(runbook_schema).validate(pilot_runbook_blocked)
    assert pilot_runbook_blocked["runbook_status"] == "blocked"
    assert pilot_runbook_blocked["p3_4_complete"] is False
    assert pilot_runbook_blocked["safety"]["does_not_run_conformance"] is True

    pilot_request = json.loads((examples_dir / "pilot_request.hermes.json").read_text())
    Draft202012Validator(pilot_request_schema).validate(pilot_request)
    assert pilot_request["request_status"] == "ready_to_send"
    assert pilot_request["p3_4_complete"] is False
    assert pilot_request["safety"]["does_not_invoke_private_adapter_command"] is True

    pilot_artifact_review_blocked = json.loads(
        (examples_dir / "pilot_artifact_review.blocked.json").read_text()
    )
    Draft202012Validator(artifact_review_schema).validate(pilot_artifact_review_blocked)
    assert pilot_artifact_review_blocked["review_status"] == "blocked"
    assert pilot_artifact_review_blocked["p3_4_complete"] is False
    assert pilot_artifact_review_blocked["safety"]["does_not_run_conformance"] is True

    pilot_evidence_manifest_blocked = json.loads(
        (examples_dir / "pilot_evidence_manifest.blocked.json").read_text()
    )
    Draft202012Validator(evidence_manifest_schema).validate(pilot_evidence_manifest_blocked)
    assert pilot_evidence_manifest_blocked["manifest_status"] == "blocked_missing_artifacts"
    assert pilot_evidence_manifest_blocked["p3_4_complete"] is False
    assert pilot_evidence_manifest_blocked["safety"]["does_not_create_archive_by_default"] is True



def test_host_shell_pilot_request_schema_and_manifests_are_declared():
    request_path = PACKAGING_DIR / "host-shell-pilot-request.schema.json"

    assert request_path.exists()

    request = json.loads(request_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert request["additionalProperties"] is False
    assert request["properties"]["schema_version"]["const"] == "kaka.host_shell_pilot_request.v1"
    assert request["properties"]["surface"]["const"] == "hermes_openclaw_host_shell_pilot_request"
    assert request["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert request["properties"]["request_status"]["const"] == "ready_to_send"
    assert request["properties"]["runtime_side_only"]["const"] is True
    assert request["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert request["properties"]["p3_4_complete"]["const"] is False
    assert request["properties"]["required_host_deliverables"]["items"]["additionalProperties"] is False
    assert request["properties"]["expected_runtime_kit_artifacts"]["items"]["additionalProperties"] is False
    assert request["properties"]["safety"]["properties"]["does_not_invoke_private_adapter_command"]["const"] is True
    assert request["properties"]["safety"]["properties"]["does_not_run_conformance"]["const"] is True
    assert request["properties"]["safety"]["properties"]["does_not_fetch_audit_refs"]["const"] is True

    valid_request = json.loads((PACKAGING_DIR / "examples" / "pilot_request.hermes.json").read_text())
    Draft202012Validator(request).validate(valid_request)
    assert valid_request["acceptance_gates"]["can_mark_p3_4_complete"] is False
    invalid_extra = json.loads(json.dumps(valid_request))
    invalid_extra["required_host_deliverables"][0]["secret_token"] = "token"
    assert not Draft202012Validator(request).is_valid(invalid_extra)

    manifest_without_request = json.loads(json.dumps(hermes))
    del manifest_without_request["host_shell_pilot_request"]
    assert not Draft202012Validator(manifest_schema).is_valid(manifest_without_request)

    for manifest in (hermes, openclaw):
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_shell_pilot_request"] == {
            "source": "host_shell_pilot_request",
            "schema_version": "kaka.host_shell_pilot_request.v1",
            "runtime_side_only": True,
            "non_mutating": True,
            "does_not_invoke_private_adapter_command": True,
            "does_not_run_conformance": True,
            "does_not_fetch_audit_refs": True,
            "phone_api_path": "/mobile/v1",
        }
        assert manifest["entrypoints"]["host_shell_pilot_request"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-request",
            "--runtime",
            manifest["runtime"],
        ]


def test_host_shell_pilot_evidence_manifest_schema_and_manifests_are_declared():
    manifest_path = PACKAGING_DIR / "host-shell-pilot-evidence-manifest.schema.json"

    assert manifest_path.exists()

    evidence = json.loads(manifest_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert evidence["additionalProperties"] is False
    assert evidence["properties"]["schema_version"]["const"] == "kaka.host_shell_pilot_evidence_manifest.v1"
    assert evidence["properties"]["surface"]["const"] == "hermes_openclaw_host_shell_pilot_evidence_manifest"
    assert evidence["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert evidence["properties"]["manifest_status"]["enum"] == [
        "blocked_missing_artifacts",
        "blocked_artifact_review",
        "ready_for_archive",
    ]
    assert evidence["properties"]["runtime_side_only"]["const"] is True
    assert evidence["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert evidence["properties"]["p3_4_complete"]["const"] is False
    assert evidence["properties"]["package"]["additionalProperties"] is False
    assert evidence["properties"]["artifacts"]["items"]["additionalProperties"] is False
    assert evidence["properties"]["archive_gates"]["additionalProperties"] is False
    assert evidence["properties"]["safety"]["properties"]["does_not_invoke_private_adapter_command"]["const"] is True
    assert evidence["properties"]["safety"]["properties"]["does_not_create_archive_by_default"]["const"] is True
    assert evidence["properties"]["safety"]["properties"]["hashes_local_artifact_files_only"]["const"] is True

    valid_blocked = json.loads(
        (PACKAGING_DIR / "examples" / "pilot_evidence_manifest.blocked.json").read_text()
    )
    Draft202012Validator(evidence).validate(valid_blocked)
    assert valid_blocked["archive_gates"]["can_mark_p3_4_complete"] is False
    invalid_extra = json.loads(json.dumps(valid_blocked))
    invalid_extra["artifacts"][0]["secret_token"] = "token"
    assert not Draft202012Validator(evidence).is_valid(invalid_extra)

    manifest_without_evidence = json.loads(json.dumps(hermes))
    del manifest_without_evidence["host_shell_pilot_evidence_manifest"]
    assert not Draft202012Validator(manifest_schema).is_valid(manifest_without_evidence)

    for manifest in (hermes, openclaw):
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_shell_pilot_evidence_manifest"] == {
            "source": "host_shell_pilot_evidence_manifest",
            "schema_version": "kaka.host_shell_pilot_evidence_manifest.v1",
            "runtime_side_only": True,
            "non_mutating": True,
            "does_not_invoke_private_adapter_command": True,
            "does_not_run_conformance": True,
            "does_not_fetch_audit_refs": True,
            "does_not_submit_handoff": True,
            "does_not_create_archive_by_default": True,
            "phone_api_path": "/mobile/v1",
        }
        assert manifest["entrypoints"]["host_shell_pilot_evidence_manifest"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-evidence-manifest",
            "--runtime",
            manifest["runtime"],
        ]


def test_host_private_adapter_conformance_schema_and_manifests_are_declared():
    conformance_path = PACKAGING_DIR / "host-private-adapter-conformance.schema.json"

    assert conformance_path.exists()

    conformance = json.loads(conformance_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert conformance["additionalProperties"] is False
    assert conformance["properties"]["schema_version"]["const"] == "kaka.host_private_adapter_conformance.v1"
    assert conformance["properties"]["surface"]["const"] == "hermes_openclaw_host_private_adapter_conformance"
    assert conformance["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert conformance["properties"]["runtime_side_only"]["const"] is True
    assert conformance["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert conformance["properties"]["phone_api_unchanged"]["const"] is True
    assert conformance["properties"]["required_capabilities"]["items"]["enum"] == list(
        HOST_PRIVATE_ADAPTER_CAPABILITIES
    )
    assert conformance["properties"]["required_action_ids"]["items"]["enum"] == list(HOST_ADAPTER_ACTIONS)
    assert conformance["properties"]["summary"]["additionalProperties"] is False
    assert conformance["properties"]["cases"]["items"]["additionalProperties"] is False
    assert conformance["properties"]["negative_checks"]["items"]["additionalProperties"] is False
    assert conformance["properties"]["safety"]["additionalProperties"] is False
    assert "host_private_adapter_conformance" in manifest_schema["required"]
    assert manifest_schema["properties"]["host_private_adapter_conformance"]["required"] == [
        "source",
        "report_schema",
        "runtime_side_only",
        "requires_configured_private_adapter_command",
        "phone_api_path",
    ]
    assert (
        manifest_schema["properties"]["host_private_adapter_conformance"]["properties"]["source"]["const"]
        == "kaka_mobile_runtime_kit host-private-adapter-conformance"
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_conformance"]["properties"]["report_schema"][
            "const"
        ]
        == "kaka.host_private_adapter_conformance.v1"
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_conformance"]["properties"][
            "runtime_side_only"
        ]["const"]
        is True
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_conformance"]["properties"][
            "requires_configured_private_adapter_command"
        ]["const"]
        is True
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_conformance"]["properties"]["phone_api_path"][
            "const"
        ]
        == "/mobile/v1"
    )
    expected_contract = {
        "source": "kaka_mobile_runtime_kit host-private-adapter-conformance",
        "report_schema": "kaka.host_private_adapter_conformance.v1",
        "runtime_side_only": True,
        "requires_configured_private_adapter_command": True,
        "phone_api_path": "/mobile/v1",
    }
    assert hermes["host_private_adapter_conformance"] == expected_contract
    assert openclaw["host_private_adapter_conformance"] == expected_contract


def test_host_shell_pilot_receipt_schema_and_manifests_are_declared():
    pilot_path = PACKAGING_DIR / "host-shell-pilot-receipt.schema.json"

    assert pilot_path.exists()

    pilot = json.loads(pilot_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert pilot["additionalProperties"] is False
    assert pilot["properties"]["schema_version"]["const"] == "kaka.host_shell_pilot_receipt.v1"
    assert pilot["properties"]["surface"]["const"] == "hermes_openclaw_external_host_shell_pilot"
    assert pilot["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert pilot["properties"]["status"]["enum"] == ["ready", "not_ready", "synthetic_only"]
    assert pilot["properties"]["runtime_side_only"]["const"] is True
    assert pilot["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert pilot["properties"]["phone_api_unchanged"]["const"] is True
    assert pilot["properties"]["external_binary_required"]["const"] is True
    assert pilot["properties"]["binary_owner"]["const"] == "host_shell"
    assert pilot["properties"]["private_adapter_command"]["additionalProperties"] is False
    assert pilot["properties"]["private_adapter_command"]["properties"]["source"]["enum"] == [
        "missing",
        "argument",
        "environment_variable",
        "manifest_entrypoint",
        "well_known_path",
    ]
    assert pilot["properties"]["distribution"]["additionalProperties"] is False
    assert pilot["properties"]["distribution"]["properties"]["evidence"]["additionalProperties"] is False
    assert "signature_subject" in (
        pilot["properties"]["distribution"]["properties"]["evidence"]["properties"]
    )
    assert pilot["properties"]["conformance"]["additionalProperties"] is False
    assert pilot["properties"]["drills"]["additionalProperties"] is False
    assert pilot["properties"]["drills"]["properties"]["evidence"]["additionalProperties"] is False
    assert "release_notes_ref" in pilot["properties"]["drills"]["properties"]["evidence"]["properties"]
    assert pilot["properties"]["release_readiness"]["additionalProperties"] is False
    assert pilot["properties"]["safety"]["additionalProperties"] is False
    invalid_ready_receipt = {
        "schema_version": "kaka.host_shell_pilot_receipt.v1",
        "surface": "hermes_openclaw_external_host_shell_pilot",
        "runtime": "hermes",
        "ok": True,
        "status": "ready",
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "external_binary_required": True,
        "binary_owner": "host_shell",
        "distribution_owner": "hermes",
        "private_adapter_command": {
            "provided": False,
            "path": "",
            "source": "missing",
            "outside_kaka_repo": False,
        },
        "distribution": {
            "source": "local_checkout",
            "channel": "development",
            "package_version": "development",
            "host_api_level": "preview",
            "native_channel_verified": False,
            "signature_verified": False,
            "update_feed_verified": False,
        },
        "conformance": {
            "required": True,
            "ran": False,
            "ok": False,
            "synthetic_only": False,
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
            },
        },
        "drills": {
            "install_verified": False,
            "update_verified": False,
            "failure_recovery_verified": False,
            "release_notes_verified": False,
        },
        "release_readiness": {
            "can_start_external_pilot": True,
            "can_mark_p3_4_complete": True,
            "blocking_reasons": ["missing_private_adapter_command"],
        },
        "safety": {
            "runtime_side_only": True,
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_proprietary_binary_bundled_by_kaka": True,
        },
    }
    assert not Draft202012Validator(pilot).is_valid(invalid_ready_receipt)
    invalid_ready_empty_path = json.loads(json.dumps(invalid_ready_receipt))
    invalid_ready_empty_path["private_adapter_command"] = {
        "provided": True,
        "path": "",
        "source": "argument",
        "outside_kaka_repo": True,
    }
    invalid_ready_empty_path["distribution"] = {
        "source": "signed_download",
        "channel": "stable",
        "package_version": "1.0.0",
        "host_api_level": "v1",
        "native_channel_verified": True,
        "signature_verified": True,
        "update_feed_verified": True,
    }
    invalid_ready_empty_path["conformance"] = {
        "required": True,
        "ran": True,
        "ok": True,
        "synthetic_only": False,
        "summary": {
            "total": 9,
            "passed": 9,
            "failed": 0,
        },
    }
    invalid_ready_empty_path["drills"] = {
        "install_verified": True,
        "update_verified": True,
        "failure_recovery_verified": True,
        "release_notes_verified": True,
    }
    invalid_ready_empty_path["release_readiness"] = {
        "can_start_external_pilot": True,
        "can_mark_p3_4_complete": True,
        "blocking_reasons": [],
    }
    assert not Draft202012Validator(pilot).is_valid(invalid_ready_empty_path)
    invalid_source = json.loads(json.dumps(invalid_ready_empty_path))
    invalid_source["private_adapter_command"]["source"] = "path_search"
    invalid_source["private_adapter_command"]["path"] = "/opt/Hermes/Kaka/hermes-kaka-host-api"
    assert not Draft202012Validator(pilot).is_valid(invalid_source)
    invalid_distribution_evidence = json.loads(json.dumps(invalid_ready_empty_path))
    invalid_distribution_evidence["distribution"]["evidence"] = {
        "signature_subject": "Developer ID Application: Example Hermes Team",
        "secret_signing_key_path": "/private/signing/key.p12",
    }
    assert not Draft202012Validator(pilot).is_valid(invalid_distribution_evidence)
    invalid_drill_evidence = json.loads(json.dumps(invalid_ready_empty_path))
    invalid_drill_evidence["drills"]["evidence"] = {
        "release_notes_ref": "https://example.invalid/release-notes",
        "host_log_path": "/private/var/log/hermes/kaka.log",
    }
    assert not Draft202012Validator(pilot).is_valid(invalid_drill_evidence)

    manifest_without_receipt = json.loads(json.dumps(hermes))
    del manifest_without_receipt["host_shell_pilot_receipt"]
    assert not Draft202012Validator(manifest_schema).is_valid(manifest_without_receipt)
    manifest_with_host_private_command = json.loads(json.dumps(hermes))
    manifest_with_host_private_command["host_private_adapter"]["command"] = (
        "/Users/example/Library/Application Support/Hermes/Kaka/hermes-kaka-host-api"
    )
    Draft202012Validator(manifest_schema).validate(manifest_with_host_private_command)

    for manifest in (hermes, openclaw):
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_shell_pilot_receipt"] == {
            "source": "host_shell_pilot_report",
            "schema_version": "kaka.host_shell_pilot_receipt.v1",
            "runtime_side_only": True,
            "binary_owner": "host_shell",
            "external_binary_required": True,
            "requires_real_external_command": True,
            "phone_api_path": "/mobile/v1",
        }
        assert manifest["entrypoints"]["host_shell_pilot_report"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-report",
            "--runtime",
            manifest["runtime"],
        ]


def test_host_shell_pilot_handoff_schema_and_manifests_are_declared():
    handoff_path = PACKAGING_DIR / "host-shell-pilot-handoff.schema.json"

    assert handoff_path.exists()

    handoff = json.loads(handoff_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert handoff["additionalProperties"] is False
    assert handoff["properties"]["schema_version"]["const"] == "kaka.host_shell_pilot_handoff.v1"
    assert handoff["properties"]["surface"]["const"] == "hermes_openclaw_host_shell_pilot_handoff"
    assert handoff["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert handoff["properties"]["handoff_status"]["enum"] == ["ready_to_submit", "incomplete"]
    assert handoff["properties"]["runtime_side_only"]["const"] is True
    assert handoff["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert handoff["properties"]["phone_api_unchanged"]["const"] is True
    assert handoff["properties"]["pilot_receipt"]["type"] == "object"
    assert handoff["properties"]["audit_refs"]["additionalProperties"] is False
    assert handoff["properties"]["release_handoff"]["additionalProperties"] is False
    assert handoff["properties"]["safety"]["additionalProperties"] is False

    valid_ready = {
        "schema_version": "kaka.host_shell_pilot_handoff.v1",
        "surface": "hermes_openclaw_host_shell_pilot_handoff",
        "runtime": "hermes",
        "ok": True,
        "handoff_status": "ready_to_submit",
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "p3_4_complete": False,
        "p3_4_completion_owner": "external_host_shell",
        "pilot_receipt": {},
        "audit_refs": {
            "required": True,
            "complete": True,
            "distribution": {
                "provided": [
                    "native_channel_ref",
                    "signature_subject",
                    "notarization_team_id",
                    "update_feed_ref",
                ],
                "missing": [],
            },
            "drills": {
                "provided": [
                    "install_receipt_ref",
                    "update_receipt_ref",
                    "failure_recovery_receipt_ref",
                    "release_notes_ref",
                ],
                "missing": [],
            },
        },
        "deliverables": [
            {
                "id": "private_adapter_command",
                "owner": "host_shell",
                "required": True,
                "status": "provided",
            }
        ],
        "release_handoff": {
            "can_submit_to_external_pilot": True,
            "can_mark_p3_4_complete": False,
            "blocking_reasons": [],
        },
        "safety": {
            "runtime_side_only": True,
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_proprietary_binary_bundled_by_kaka": True,
            "does_not_fetch_audit_refs": True,
            "does_not_change_receipt_gate": True,
        },
    }
    Draft202012Validator(handoff).validate(valid_ready)
    invalid_extra = json.loads(json.dumps(valid_ready))
    invalid_extra["audit_refs"]["secret_signing_key_path"] = "/private/key.p12"
    assert not Draft202012Validator(handoff).is_valid(invalid_extra)
    invalid_ready_with_blockers = json.loads(json.dumps(valid_ready))
    invalid_ready_with_blockers["release_handoff"]["blocking_reasons"] = [
        "missing_audit_ref:native_channel_ref",
    ]
    assert not Draft202012Validator(handoff).is_valid(invalid_ready_with_blockers)

    manifest_without_handoff = json.loads(json.dumps(hermes))
    del manifest_without_handoff["host_shell_pilot_handoff"]
    assert not Draft202012Validator(manifest_schema).is_valid(manifest_without_handoff)

    for manifest in (hermes, openclaw):
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_shell_pilot_handoff"] == {
            "source": "host_shell_pilot_handoff",
            "schema_version": "kaka.host_shell_pilot_handoff.v1",
            "runtime_side_only": True,
            "requires_pilot_receipt": True,
            "requires_all_audit_refs": True,
            "phone_api_path": "/mobile/v1",
        }
        assert manifest["entrypoints"]["host_shell_pilot_handoff"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-handoff",
            "--runtime",
            manifest["runtime"],
        ]


def test_host_shell_pilot_preflight_schema_and_manifests_are_declared():
    preflight_path = PACKAGING_DIR / "host-shell-pilot-preflight.schema.json"

    assert preflight_path.exists()

    preflight = json.loads(preflight_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert preflight["additionalProperties"] is False
    assert preflight["properties"]["schema_version"]["const"] == "kaka.host_shell_pilot_preflight.v1"
    assert preflight["properties"]["surface"]["const"] == "hermes_openclaw_host_shell_pilot_preflight"
    assert preflight["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert preflight["properties"]["status"]["enum"] == ["ready_for_conformance", "blocked"]
    assert preflight["properties"]["runtime_side_only"]["const"] is True
    assert preflight["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert preflight["properties"]["p3_4_complete"]["const"] is False
    assert preflight["properties"]["host_shell"]["additionalProperties"] is False
    assert preflight["properties"]["private_adapter_command"]["additionalProperties"] is False
    assert preflight["properties"]["safety"]["properties"]["does_not_invoke_private_adapter_command"]["const"] is True

    valid_not_ready = {
        "schema_version": "kaka.host_shell_pilot_preflight.v1",
        "surface": "hermes_openclaw_host_shell_pilot_preflight",
        "runtime": "hermes",
        "ok": False,
        "status": "blocked",
        "runtime_side_only": True,
        "phone_api_path": "/mobile/v1",
        "phone_api_unchanged": True,
        "p3_4_complete": False,
        "host_shell": {
            "detected": False,
            "candidates": [],
            "cli": {
                "command": "hermes",
                "found": False,
                "path": "",
            },
        },
        "private_adapter_command": {
            "default_command_name": "hermes-kaka-host-api",
            "selected": {
                "provided": False,
                "source": "missing",
                "path": "",
                "exists": False,
                "executable": False,
                "outside_kaka_repo": False,
            },
            "environment_variable": {
                "name": "HERMES_KAKA_HOST_API",
                "configured": False,
                "path": "",
                "exists": False,
                "executable": False,
            },
            "manifest_entrypoint": {
                "configured": False,
                "manifest_path": "runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json",
                "path": "",
                "exists": False,
                "executable": False,
            },
            "well_known_paths": [],
            "path_command": {
                "command": "hermes-kaka-host-api",
                "found": False,
                "path": "",
                "informational_only": True,
            },
        },
        "handoff_command": [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-handoff",
            "--runtime",
            "hermes",
        ],
        "release_preflight": {
            "can_run_conformance": False,
            "can_mark_p3_4_complete": False,
            "blocking_reasons": [
                "missing_host_shell",
                "missing_private_adapter_command",
            ],
        },
        "next_actions": [
            "install_or_open_host_shell",
            "provide_private_adapter_command",
        ],
        "safety": {
            "runtime_side_only": True,
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_proprietary_binary_bundled_by_kaka": True,
            "does_not_invoke_private_adapter_command": True,
            "does_not_run_conformance": True,
            "does_not_fetch_audit_refs": True,
        },
    }
    Draft202012Validator(preflight).validate(valid_not_ready)
    invalid_extra = json.loads(json.dumps(valid_not_ready))
    invalid_extra["private_adapter_command"]["secret_env_value"] = "token"
    assert not Draft202012Validator(preflight).is_valid(invalid_extra)

    manifest_without_preflight = json.loads(json.dumps(hermes))
    del manifest_without_preflight["host_shell_pilot_preflight"]
    assert not Draft202012Validator(manifest_schema).is_valid(manifest_without_preflight)

    for manifest in (hermes, openclaw):
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_shell_pilot_preflight"] == {
            "source": "host_shell_pilot_preflight",
            "schema_version": "kaka.host_shell_pilot_preflight.v1",
            "runtime_side_only": True,
            "non_mutating": True,
            "does_not_invoke_private_adapter_command": True,
            "phone_api_path": "/mobile/v1",
        }
        assert manifest["entrypoints"]["host_shell_pilot_preflight"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-preflight",
            "--runtime",
            manifest["runtime"],
        ]


def test_host_shell_pilot_runbook_schema_and_manifests_are_declared():
    runbook_path = PACKAGING_DIR / "host-shell-pilot-runbook.schema.json"

    assert runbook_path.exists()

    runbook = json.loads(runbook_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert runbook["additionalProperties"] is False
    assert runbook["properties"]["schema_version"]["const"] == "kaka.host_shell_pilot_runbook.v1"
    assert runbook["properties"]["surface"]["const"] == "hermes_openclaw_host_shell_pilot_runbook"
    assert runbook["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert runbook["properties"]["runbook_status"]["enum"] == [
        "ready_for_conformance",
        "blocked",
    ]
    assert runbook["properties"]["runtime_side_only"]["const"] is True
    assert runbook["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert runbook["properties"]["p3_4_complete"]["const"] is False
    assert runbook["properties"]["brief"]["additionalProperties"] is False
    assert runbook["properties"]["pilot_target"]["additionalProperties"] is False
    assert runbook["properties"]["preflight"]["additionalProperties"] is False
    assert runbook["properties"]["ordered_steps"]["items"]["additionalProperties"] is False
    assert runbook["properties"]["command_artifacts"]["additionalProperties"] is False
    assert runbook["properties"]["evidence_requirements"]["additionalProperties"] is False
    assert runbook["properties"]["acceptance_gates"]["additionalProperties"] is False
    assert runbook["properties"]["safety"]["properties"]["does_not_invoke_private_adapter_command"]["const"] is True
    assert runbook["properties"]["safety"]["properties"]["does_not_run_conformance"]["const"] is True
    assert runbook["properties"]["safety"]["properties"]["does_not_fetch_audit_refs"]["const"] is True

    valid_blocked = json.loads((PACKAGING_DIR / "examples" / "pilot_runbook.blocked.json").read_text())
    Draft202012Validator(runbook).validate(valid_blocked)
    assert valid_blocked["brief"]["requested_host_owner_action"] == "provide_private_adapter_command"
    assert valid_blocked["pilot_target"]["manifest_key"] == "host_private_adapter.command"
    assert valid_blocked["command_artifacts"]["host_shell_pilot_handoff"][3] == "host-shell-pilot-handoff"
    assert valid_blocked["evidence_requirements"]["distribution"]["items"][0]["cli_flag"] == "--native-channel-ref"
    assert valid_blocked["acceptance_gates"]["can_mark_p3_4_complete"] is False
    invalid_extra = json.loads(json.dumps(valid_blocked))
    invalid_extra["ordered_steps"][0]["secret_token"] = "token"
    assert not Draft202012Validator(runbook).is_valid(invalid_extra)

    manifest_without_runbook = json.loads(json.dumps(hermes))
    del manifest_without_runbook["host_shell_pilot_runbook"]
    assert not Draft202012Validator(manifest_schema).is_valid(manifest_without_runbook)

    for manifest in (hermes, openclaw):
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_shell_pilot_runbook"] == {
            "source": "host_shell_pilot_runbook",
            "schema_version": "kaka.host_shell_pilot_runbook.v1",
            "runtime_side_only": True,
            "non_mutating": True,
            "does_not_invoke_private_adapter_command": True,
            "does_not_run_conformance": True,
            "phone_api_path": "/mobile/v1",
        }
        assert manifest["entrypoints"]["host_shell_pilot_runbook"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-runbook",
            "--runtime",
            manifest["runtime"],
        ]


def test_host_shell_pilot_artifact_review_schema_and_manifests_are_declared():
    review_path = PACKAGING_DIR / "host-shell-pilot-artifact-review.schema.json"

    assert review_path.exists()

    review = json.loads(review_path.read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    hermes = json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text())
    openclaw = json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text())

    assert review["additionalProperties"] is False
    assert review["properties"]["schema_version"]["const"] == "kaka.host_shell_pilot_artifact_review.v1"
    assert review["properties"]["surface"]["const"] == "hermes_openclaw_host_shell_pilot_artifact_review"
    assert review["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert review["properties"]["review_status"]["enum"] == [
        "ready_for_external_review",
        "blocked",
    ]
    assert review["properties"]["runtime_side_only"]["const"] is True
    assert review["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert review["properties"]["p3_4_complete"]["const"] is False
    assert review["properties"]["artifacts"]["additionalProperties"] is False
    assert review["properties"]["artifact_consistency"]["additionalProperties"] is False
    assert review["properties"]["release_review"]["additionalProperties"] is False
    assert review["properties"]["safety"]["properties"]["does_not_invoke_private_adapter_command"]["const"] is True
    assert review["properties"]["safety"]["properties"]["does_not_run_conformance"]["const"] is True
    assert review["properties"]["safety"]["properties"]["does_not_fetch_audit_refs"]["const"] is True

    valid_blocked = json.loads(
        (PACKAGING_DIR / "examples" / "pilot_artifact_review.blocked.json").read_text()
    )
    Draft202012Validator(review).validate(valid_blocked)
    assert valid_blocked["release_review"]["can_mark_p3_4_complete"] is False
    invalid_extra = json.loads(json.dumps(valid_blocked))
    invalid_extra["artifacts"]["preflight"]["secret_token"] = "token"
    assert not Draft202012Validator(review).is_valid(invalid_extra)

    manifest_without_review = json.loads(json.dumps(hermes))
    del manifest_without_review["host_shell_pilot_artifact_review"]
    assert not Draft202012Validator(manifest_schema).is_valid(manifest_without_review)

    for manifest in (hermes, openclaw):
        Draft202012Validator(manifest_schema).validate(manifest)
        assert manifest["host_shell_pilot_artifact_review"] == {
            "source": "host_shell_pilot_artifact_review",
            "schema_version": "kaka.host_shell_pilot_artifact_review.v1",
            "runtime_side_only": True,
            "non_mutating": True,
            "does_not_invoke_private_adapter_command": True,
            "does_not_run_conformance": True,
            "does_not_fetch_audit_refs": True,
            "phone_api_path": "/mobile/v1",
        }
        assert manifest["entrypoints"]["host_shell_pilot_artifact_review"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-shell-pilot-artifact-review",
            "--runtime",
            manifest["runtime"],
        ]


def test_packaging_schema_files_define_required_shell_contracts():
    settings_schema = json.loads((PACKAGING_DIR / "settings-preview.schema.json").read_text())
    manifest_schema = json.loads((PACKAGING_DIR / "runtime-shell-manifest.schema.json").read_text())
    host_package_schema = json.loads((PACKAGING_DIR / "host-package.schema.json").read_text())

    assert settings_schema["properties"]["surface"]["const"] == "runtime_side_settings_preview"
    assert "runtime_side_ui" in settings_schema["required"]
    assert "actions" in settings_schema["required"]
    assert settings_schema["properties"]["phone_safe_summary"]["additionalProperties"] is False
    assert "consumer_ui" in settings_schema["properties"]["runtime_side_ui"]["required"]
    assert "process_ownership" in settings_schema["properties"]["runtime_side_ui"]["required"]
    assert (
        settings_schema["properties"]["runtime_side_ui"]["properties"]["consumer_ui"]["properties"]["surface"][
            "const"
        ]
        == "hermes_openclaw_consumer_runtime_ui"
    )
    assert (
        settings_schema["properties"]["runtime_side_ui"]["properties"]["process_ownership"]["properties"][
            "schema_version"
        ]["const"]
        == "kaka.runtime_process_ownership.v1"
    )
    assert (
        settings_schema["properties"]["runtime_side_ui"]["properties"]["process_ownership"]["properties"]["surface"][
            "const"
        ]
        == "hermes_openclaw_process_ownership"
    )
    settings_controls = settings_schema["properties"]["runtime_side_ui"]["properties"]["controls"]["required"]
    for control in PROCESS_CONTROLS:
        assert control in settings_controls
    assert manifest_schema["properties"]["schema_version"]["const"] == "kaka.runtime_shell_manifest.v1"
    assert manifest_schema["properties"]["install"]["properties"]["auto_start_on_install"]["const"] is False
    assert manifest_schema["properties"]["defaults"]["properties"]["lan_exposed"]["const"] is False
    assert "consumer_ui" in manifest_schema["required"]
    assert "process_ownership" in manifest_schema["required"]
    assert (
        manifest_schema["properties"]["consumer_ui"]["properties"]["source"]["const"]
        == "settings_preview.runtime_side_ui.consumer_ui"
    )
    assert (
        manifest_schema["properties"]["process_ownership"]["properties"]["source"]["const"]
        == "settings_preview.runtime_side_ui.process_ownership"
    )
    assert (
        manifest_schema["properties"]["process_ownership"]["properties"]["schema_version"]["const"]
        == "kaka.runtime_process_ownership.v1"
    )
    assert (
        manifest_schema["properties"]["process_ownership"]["properties"]["surface"]["const"]
        == "hermes_openclaw_process_ownership"
    )
    assert "host_package" in manifest_schema["required"]
    assert manifest_schema["properties"]["host_package"]["required"] == [
        "source",
        "schema_version",
        "surface",
        "required_actions",
        "requires_host_native_adapter",
    ]
    assert "host_adapter" in manifest_schema["required"]
    assert manifest_schema["properties"]["host_adapter"]["required"] == [
        "source",
        "schema_version",
        "surface",
        "adapter_modes",
        "required_actions",
        "requires_explicit_user_approval_for_mutations",
    ]
    assert (
        manifest_schema["properties"]["host_adapter"]["properties"]["source"]["const"]
        == "kaka_mobile_runtime_kit host-adapter-run"
    )
    assert (
        manifest_schema["properties"]["host_adapter"]["properties"]["schema_version"]["const"]
        == "kaka.host_adapter_action_result.v1"
    )
    assert (
        manifest_schema["properties"]["host_adapter"]["properties"]["surface"]["const"]
        == "hermes_openclaw_host_adapter_binding"
    )
    assert (
        manifest_schema["properties"]["host_adapter"]["properties"][
            "requires_explicit_user_approval_for_mutations"
        ]["const"]
        is True
    )
    assert "host_private_adapter" in manifest_schema["required"]
    assert manifest_schema["properties"]["host_private_adapter"]["required"] == [
        "source",
        "request_schema",
        "response_schema",
        "required_capabilities",
        "runtime_side_only",
        "requires_explicit_user_approval_for_mutations",
    ]
    assert (
        manifest_schema["properties"]["host_private_adapter"]["properties"]["source"]["const"]
        == "host_adapter.private_adapter_command"
    )
    assert (
        manifest_schema["properties"]["host_private_adapter"]["properties"]["request_schema"]["const"]
        == "kaka.host_private_adapter_request.v1"
    )
    assert (
        manifest_schema["properties"]["host_private_adapter"]["properties"]["response_schema"]["const"]
        == "kaka.host_private_adapter_response.v1"
    )
    assert (
        manifest_schema["properties"]["host_private_adapter"]["properties"]["runtime_side_only"]["const"]
        is True
    )
    assert (
        manifest_schema["properties"]["host_private_adapter"]["properties"][
            "requires_explicit_user_approval_for_mutations"
        ]["const"]
        is True
    )
    assert "host_private_adapter_package" in manifest_schema["required"]
    assert manifest_schema["properties"]["host_private_adapter_package"]["required"] == [
        "source",
        "schema_version",
        "runtime_side_only",
        "binary_owner",
        "distribution_owner",
        "requires_conformance_passed",
        "phone_api_path",
    ]
    assert (
        manifest_schema["properties"]["host_private_adapter_package"]["properties"]["source"]["const"]
        == "host_package.private_adapter_package"
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_package"]["properties"]["schema_version"][
            "const"
        ]
        == "kaka.host_private_adapter_package.v1"
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_package"]["properties"]["runtime_side_only"][
            "const"
        ]
        is True
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_package"]["properties"]["binary_owner"][
            "const"
        ]
        == "host_shell"
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_package"]["properties"][
            "requires_conformance_passed"
        ]["const"]
        is True
    )
    assert (
        manifest_schema["properties"]["host_private_adapter_package"]["properties"]["phone_api_path"][
            "const"
        ]
        == "/mobile/v1"
    )
    assert "host_package_preview" in manifest_schema["properties"]["entrypoints"]["required"]
    assert "host_adapter_run" in manifest_schema["properties"]["entrypoints"]["required"]
    manifest_forbidden_requirements = manifest_schema["properties"]["forbidden_phone_safe_fields"][
        "allOf"
    ]
    for field in (
        "runtime_store_path",
        "recall_search_endpoint",
        "provider_keys",
        "auth_env_files",
        "mobile_tokens",
        "tls_private_key_paths",
        "env_file",
        "auth_file",
        "auth_files",
        "provider_credentials",
        "mobile_bearer_token",
        "tls_private_key_path",
        "hidden_prompt",
        "hidden_prompts",
        "raw_embeddings",
        "index_rows",
        "task_logs",
        "retrieval_index_rows",
        "raw_provider_responses",
        "process_ids",
        "host_log_paths",
    ):
        assert {"contains": {"const": field}} in manifest_forbidden_requirements
    assert host_package_schema["$schema"] == "http://json-schema.org/draft-07/schema#"
    assert host_package_schema["properties"]["schema_version"]["const"] == "kaka.runtime_host_package.v1"
    assert host_package_schema["properties"]["surface"]["const"] == "hermes_openclaw_host_package"
    assert host_package_schema["properties"]["runtime"]["enum"] == ["hermes", "openclaw"]
    assert host_package_schema["required"] == [
        "schema_version",
        "surface",
        "runtime",
        "host_api_level",
        "distribution",
        "private_adapter_package",
        "install_policy",
        "host_actions",
        "artifacts",
        "process_ownership",
        "consumer_ui",
        "safety",
    ]
    assert (
        host_package_schema["properties"]["distribution"]["properties"]["update_policy"]["const"]
        == "explicit_user_approved"
    )
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["schema_version"]["const"]
        == "kaka.host_private_adapter_package.v1"
    )
    assert host_package_schema["properties"]["private_adapter_package"]["required"] == [
        "schema_version",
        "surface",
        "runtime",
        "binary",
        "discovery",
        "distribution",
        "validation",
        "required_action_ids",
        "required_capabilities",
        "mobile_bridge",
        "safety",
    ]
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["binary"]["properties"][
            "owner"
        ]["const"]
        == "host_shell"
    )
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["binary"]["properties"][
            "private_api_implementation"
        ]["const"]
        == "not_bundled_in_kaka"
    )
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["discovery"][
            "properties"
        ]["config_key"]["const"]
        == "private_adapter_command"
    )
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["discovery"][
            "properties"
        ]["manifest_entrypoint"]["const"]
        == "host_private_adapter.command"
    )
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["distribution"][
            "properties"
        ]["download_owner"]["const"]
        == "host_shell"
    )
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["distribution"][
            "properties"
        ]["signature_policy"]["const"]
        == "host_shell_required"
    )
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["validation"][
            "properties"
        ]["requires_conformance_passed"]["const"]
        is True
    )
    private_package_schema = host_package_schema["properties"]["private_adapter_package"]
    assert private_package_schema["additionalProperties"] is False
    assert private_package_schema["properties"]["binary"]["additionalProperties"] is False
    assert private_package_schema["properties"]["discovery"]["additionalProperties"] is False
    assert private_package_schema["properties"]["distribution"]["additionalProperties"] is False
    assert private_package_schema["properties"]["validation"]["additionalProperties"] is False
    assert private_package_schema["properties"]["safety"]["additionalProperties"] is False
    assert private_package_schema["properties"]["required_action_ids"]["minItems"] == len(
        HOST_ADAPTER_ACTIONS
    )
    assert private_package_schema["properties"]["required_capabilities"]["minItems"] == len(
        HOST_PRIVATE_ADAPTER_CAPABILITIES
    )
    package_forbidden_requirements = private_package_schema["properties"]["safety"]["properties"][
        "forbidden_phone_safe_fields"
    ]["allOf"]
    for field in (
        "runtime_store_path",
        "recall_search_endpoint",
        "provider_keys",
        "auth_env_files",
        "mobile_tokens",
        "tls_private_key_paths",
        "env_file",
        "auth_file",
        "auth_files",
        "provider_credentials",
        "mobile_bearer_token",
        "tls_private_key_path",
        "hidden_prompt",
        "hidden_prompts",
        "raw_embeddings",
        "index_rows",
        "retrieval_index_rows",
        "task_logs",
        "raw_provider_responses",
        "process_ids",
        "host_log_paths",
    ):
        assert {"contains": {"const": field}} in package_forbidden_requirements
    assert (
        host_package_schema["properties"]["private_adapter_package"]["properties"]["mobile_bridge"][
            "properties"
        ]["phone_api_path"]["const"]
        == "/mobile/v1"
    )
    assert (
        host_package_schema["properties"]["install_policy"]["properties"]["auto_start_on_install"]["const"]
        is False
    )
    assert (
        host_package_schema["properties"]["install_policy"]["properties"]["enabled_by_default"]["const"]
        is False
    )
    assert (
        host_package_schema["properties"]["install_policy"]["properties"]["login_item_default"]["const"]
        is False
    )
    assert (
        host_package_schema["properties"]["install_policy"]["properties"]["creates_login_item_on_install"][
            "const"
        ]
        is False
    )
    assert host_package_schema["properties"]["host_actions"]["items"]["required"] == [
        "id",
        "owner",
        "adapter",
        "mutates_host_state",
        "requires_explicit_user_approval",
        "runtime_side_only",
        "enabled",
    ]
    assert (
        host_package_schema["properties"]["host_actions"]["items"]["properties"]["owner"]["const"]
        == "host_native_adapter"
    )
    assert (
        host_package_schema["properties"]["host_actions"]["items"]["properties"]["runtime_side_only"]["const"]
        is True
    )
    assert host_package_schema["properties"]["safety"]["properties"]["runtime_side_only"]["const"] is True
    assert host_package_schema["properties"]["safety"]["properties"]["phone_settings_owner"]["const"] is False
    assert (
        host_package_schema["properties"]["safety"]["properties"]["no_autostart_on_install"]["const"]
        is True
    )
    assert (
        host_package_schema["properties"]["safety"]["properties"]["no_login_item_creation_by_runtime_kit"][
            "const"
        ]
        is True
    )
    assert (
        host_package_schema["properties"]["safety"]["properties"]["requires_host_native_adapter"]["const"]
        is True
    )
    assert "forbidden_phone_safe_fields" in host_package_schema["properties"]["safety"]["required"]
    forbidden_requirements = host_package_schema["properties"]["safety"]["properties"][
        "forbidden_phone_safe_fields"
    ]["allOf"]
    assert {"contains": {"const": "hidden_prompt"}} in forbidden_requirements
    assert {"contains": {"const": "hidden_prompts"}} in forbidden_requirements


def test_runtime_shell_manifests_match_static_contract():
    manifests = [
        json.loads(Path("runtime-kit/hermes-plugin/kaka-mobile-bridge.package.json").read_text()),
        json.loads(Path("runtime-kit/openclaw-skill/kaka-mobile-bridge.sidecar.json").read_text()),
    ]

    for manifest in manifests:
        assert manifest["schema_version"] == "kaka.runtime_shell_manifest.v1"
        assert manifest["id"] == "kaka-mobile-bridge"
        assert manifest["install"] == {
            "enabled_by_default": False,
            "auto_start_on_install": False,
            "requires_explicit_start": True,
        }
        assert manifest["defaults"]["lan_exposed"] is False
        assert manifest["defaults"]["bonjour"] is False
        assert manifest["defaults"]["start_with_runtime"] is False
        assert manifest["consumer_ui"] == {
            "source": "settings_preview.runtime_side_ui.consumer_ui",
            "schema_version": "kaka.runtime_consumer_ui.v1",
            "surface": "hermes_openclaw_consumer_runtime_ui",
            "required_sections": ["process", "connection", "pairing", "memory", "retrieval"],
            "required_primary_actions": ["start_bridge", "stop_bridge", "show_qr", "revoke_mobile_tokens"],
        }
        assert manifest["process_ownership"] == {
            "source": "settings_preview.runtime_side_ui.process_ownership",
            "schema_version": "kaka.runtime_process_ownership.v1",
            "surface": "hermes_openclaw_process_ownership",
            "required_actions": list(PROCESS_ACTIONS),
            "requires_explicit_user_approval": True,
        }
        assert manifest["host_package"] == {
            "source": "kaka_mobile_runtime_kit host-package-preview",
            "schema_version": "kaka.runtime_host_package.v1",
            "surface": "hermes_openclaw_host_package",
            "required_actions": list(HOST_PACKAGE_ACTIONS),
            "requires_host_native_adapter": True,
        }
        assert manifest["host_adapter"] == {
            "source": "kaka_mobile_runtime_kit host-adapter-run",
            "schema_version": "kaka.host_adapter_action_result.v1",
            "surface": "hermes_openclaw_host_adapter_binding",
            "adapter_modes": ["mock", "private"],
            "required_actions": list(HOST_ADAPTER_ACTIONS),
            "requires_explicit_user_approval_for_mutations": True,
        }
        assert manifest["host_private_adapter"] == {
            "source": "host_adapter.private_adapter_command",
            "request_schema": "kaka.host_private_adapter_request.v1",
            "response_schema": "kaka.host_private_adapter_response.v1",
            "required_capabilities": list(HOST_PRIVATE_ADAPTER_CAPABILITIES),
            "runtime_side_only": True,
            "requires_explicit_user_approval_for_mutations": True,
        }
        assert manifest["host_private_adapter_package"] == {
            "source": "host_package.private_adapter_package",
            "schema_version": "kaka.host_private_adapter_package.v1",
            "runtime_side_only": True,
            "binary_owner": "host_shell",
            "distribution_owner": manifest["runtime"],
            "requires_conformance_passed": True,
            "phone_api_path": "/mobile/v1",
        }
        for control in (
            "pairing_mode",
            "qr_ttl_seconds",
            "trusted_local_tls",
            "revoke_mobile_tokens",
        ):
            assert control in manifest["controls"]
        for control in PROCESS_CONTROLS:
            assert control in manifest["controls"]
        assert "settings_preview" in manifest["entrypoints"]
        assert "package_preview" in manifest["entrypoints"]
        assert manifest["entrypoints"]["host_package_preview"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-package-preview",
            "--runtime",
            manifest["runtime"],
        ]
        assert manifest["entrypoints"]["host_adapter_run"] == [
            "python3",
            "-m",
            "kaka_mobile_runtime_kit",
            "host-adapter-run",
            "--runtime",
            manifest["runtime"],
        ]
        assert "start_bridge" in manifest["entrypoints"]
        assert "runtime_store_path" in manifest["runtime_side_values"]
        assert "recall_search_endpoint" in manifest["runtime_side_values"]
        assert "runtime_store_path" in manifest["forbidden_phone_safe_fields"]
        assert "recall_search_endpoint" in manifest["forbidden_phone_safe_fields"]
        assert "provider_keys" in manifest["forbidden_phone_safe_fields"]
        assert "auth_env_files" in manifest["forbidden_phone_safe_fields"]
        assert "auth_file" in manifest["forbidden_phone_safe_fields"]
        assert "auth_files" in manifest["forbidden_phone_safe_fields"]
        assert "hidden_prompt" in manifest["forbidden_phone_safe_fields"]
        assert "hidden_prompts" in manifest["forbidden_phone_safe_fields"]
        assert "task_logs" in manifest["forbidden_phone_safe_fields"]
        assert "process_ids" in manifest["forbidden_phone_safe_fields"]
        assert "host_log_paths" in manifest["forbidden_phone_safe_fields"]
        assert "mobile_tokens" in manifest["forbidden_phone_safe_fields"]
        assert "mobile_bearer_token" in manifest["forbidden_phone_safe_fields"]
        assert "tls_private_key_path" in manifest["runtime_side_values"]
        assert "tls_private_key_path" in manifest["forbidden_phone_safe_fields"]
        assert "tls_private_key_paths" in manifest["forbidden_phone_safe_fields"]


def test_runtime_retention_purge_receipt_schema_is_closed_and_runtime_side_only():
    schema = json.loads((PACKAGING_DIR / "runtime-retention-purge-receipt.schema.json").read_text())

    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["schema_version"]["const"] == "kaka.runtime_retention_purge_receipt.v1"
    assert schema["properties"]["surface"]["const"] == "hermes_openclaw_runtime_retention_purge"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["mode"]["enum"] == ["dry_run", "apply"]
    assert schema["properties"]["safety"]["additionalProperties"] is False
    assert schema["properties"]["safety"]["properties"]["runtime_side_only"]["const"] is True
    assert schema["properties"]["safety"]["properties"]["phone_api_path"]["const"] == "/mobile/v1"
    assert schema["properties"]["safety"]["properties"]["phone_api_unchanged"]["const"] is True
    assert schema["properties"]["safety"]["properties"]["phone_settings_owner"]["const"] is False
    assert schema["properties"]["safety"]["properties"]["no_mobile_bridge_purge_endpoint"]["const"] is True
    assert schema["properties"]["safety"]["properties"]["no_automatic_cleanup"]["const"] is True
    assert schema["properties"]["safety"]["properties"]["no_recall_purge"]["const"] is True
    assert schema["properties"]["recall_untouched"]["const"] is True
    for top_level_phone_field in (
        "phone_api_path",
        "phone_api_unchanged",
        "phone_settings_owner",
        "no_mobile_bridge_purge_endpoint",
    ):
        assert top_level_phone_field not in schema["properties"]

    status_schema = schema["properties"]["preserved"]["properties"]["asset_purge_status"]
    assert status_schema["enum"] == [
        "complete",
        "partial_missing_asset_timestamps",
        "skipped_missing_asset_timestamps",
    ]

    valid_receipt = {
        "schema_version": "kaka.runtime_retention_purge_receipt.v1",
        "surface": "hermes_openclaw_runtime_retention_purge",
        "runtime": "hermes",
        "mode": "apply",
        "applied": True,
        "generated_at": "2026-06-07T00:00:00Z",
        "policy": {
            "input_assets_days": 7,
            "output_assets_days": 30,
            "task_history_days": 30,
        },
        "cutoffs": {
            "input_assets_before": "2026-05-31T00:00:00Z",
            "output_assets_before": "2026-05-08T00:00:00Z",
            "task_history_before": "2026-05-08T00:00:00Z",
        },
        "eligible": {
            "input_asset_ids": ["asset_old_input"],
            "output_asset_ids": ["asset_result_old_output"],
            "task_ids": [],
            "task_event_ids": [],
        },
        "deleted": {
            "input_asset_ids": ["asset_old_input"],
            "output_asset_ids": ["asset_result_old_output"],
            "task_ids": [],
            "task_event_ids": [],
        },
        "preserved": {
            "active_task_ids": [],
            "untracked_asset_ids": [],
            "asset_purge_status": "complete",
        },
        "recall_untouched": True,
        "safety": {
            "runtime_side_only": True,
            "phone_api_path": "/mobile/v1",
            "phone_api_unchanged": True,
            "phone_settings_owner": False,
            "no_mobile_bridge_purge_endpoint": True,
            "no_automatic_cleanup": True,
            "no_recall_purge": True,
        },
    }
    validator = Draft202012Validator(schema)
    validator.validate(valid_receipt)

    top_level_phone_scatter = json.loads(json.dumps(valid_receipt))
    top_level_phone_scatter["phone_api_unchanged"] = True
    assert not validator.is_valid(top_level_phone_scatter)

    unsafe_safety_extension = json.loads(json.dumps(valid_receipt))
    unsafe_safety_extension["safety"]["phone_api_owner"] = "mobile_bridge"
    assert not validator.is_valid(unsafe_safety_extension)


def test_settings_preview_schema_freezes_retention_policy_controls_and_phone_safe_allowlist():
    settings_schema = json.loads((PACKAGING_DIR / "settings-preview.schema.json").read_text())

    Draft202012Validator.check_schema(settings_schema)
    assert "retention" in settings_schema["required"]
    retention = settings_schema["properties"]["retention"]
    assert retention["additionalProperties"] is False
    assert set(retention["required"]) == {
        "input_assets_days",
        "output_assets_days",
        "task_history_days",
    }
    for key in ("input_assets_days", "output_assets_days", "task_history_days"):
        assert retention["properties"][key] == {
            "type": "integer",
            "minimum": 1,
            "maximum": 3650,
        }

    controls = settings_schema["properties"]["runtime_side_ui"]["properties"]["controls"]
    for key in ("input_assets_days", "output_assets_days", "task_history_days"):
        assert key in controls["required"]
        assert controls["properties"][key]["additionalProperties"] is False
        assert controls["properties"][key]["required"] == ["kind", "value", "minimum", "maximum"]
        assert controls["properties"][key]["properties"]["kind"]["const"] == "stepper"
        assert controls["properties"][key]["properties"]["value"] == {
            "type": "integer",
            "minimum": 1,
            "maximum": 3650,
        }
        assert controls["properties"][key]["properties"]["minimum"]["const"] == 1
        assert controls["properties"][key]["properties"]["maximum"]["const"] == 3650

    phone_safe = settings_schema["properties"]["phone_safe_summary"]
    assert phone_safe["additionalProperties"] is False
    assert set(phone_safe["required"]) == {
        "recall_store_enabled",
        "recall_store_owner",
        "semantic_recall_mode",
    }
    assert set(phone_safe["properties"]) == {
        "recall_store_enabled",
        "recall_store_owner",
        "semantic_recall_mode",
    }
    assert phone_safe["properties"]["recall_store_enabled"]["type"] == "boolean"
    assert phone_safe["properties"]["recall_store_owner"]["enum"] == ["mock_bridge", "runtime"]
    assert phone_safe["properties"]["semantic_recall_mode"]["enum"] == [
        "local_deterministic",
        "provider_backed",
    ]

    validator = Draft202012Validator(settings_schema)
    preview = build_runtime_settings_preview(
        BridgeConfig(
            runtime_store_path="/Users/kartz/.kaka/mobile-runtime.sqlite3",
            recall_search_provider="runtime_http",
            recall_search_endpoint="http://127.0.0.1:8788/kaka/recall/search",
            input_assets_days=3,
            output_assets_days=14,
            task_history_days=60,
        )
    )
    validator.validate(preview)

    leaked_phone_safe = json.loads(json.dumps(preview))
    leaked_phone_safe["phone_safe_summary"]["runtime_store_path"] = "/Users/kartz/.kaka/mobile-runtime.sqlite3"
    assert not validator.is_valid(leaked_phone_safe)
