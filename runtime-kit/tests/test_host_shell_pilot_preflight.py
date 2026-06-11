import json
from pathlib import Path

from kaka_mobile_runtime_kit.cli import BridgeConfig, main
from kaka_mobile_runtime_kit.host_shell_pilot_preflight import (
    build_host_shell_pilot_preflight,
)


def _executable(path: Path, body: str = "#!/bin/sh\nexit 99\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)
    return path


def test_preflight_reports_missing_host_shell_and_private_command(tmp_path, monkeypatch):
    monkeypatch.delenv("HERMES_KAKA_HOST_API", raising=False)

    preflight = build_host_shell_pilot_preflight(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command="",
        applications_root=tmp_path / "Applications",
        home=tmp_path / "home",
        path_env="",
    )

    assert preflight["schema_version"] == "kaka.host_shell_pilot_preflight.v1"
    assert preflight["surface"] == "hermes_openclaw_host_shell_pilot_preflight"
    assert preflight["runtime"] == "hermes"
    assert preflight["ok"] is False
    assert preflight["status"] == "blocked"
    assert preflight["runtime_side_only"] is True
    assert preflight["phone_api_path"] == "/mobile/v1"
    assert preflight["phone_api_unchanged"] is True
    assert preflight["p3_4_complete"] is False
    assert preflight["host_shell"]["detected"] is False
    assert preflight["private_adapter_command"]["selected"]["provided"] is False
    assert "missing_host_shell" in preflight["release_preflight"]["blocking_reasons"]
    assert "missing_private_adapter_command" in preflight["release_preflight"]["blocking_reasons"]
    assert preflight["release_preflight"]["can_run_conformance"] is False
    assert preflight["release_preflight"]["can_mark_p3_4_complete"] is False
    assert preflight["safety"]["does_not_invoke_private_adapter_command"] is True


def test_preflight_detects_host_shell_app_and_cli_without_command(tmp_path, monkeypatch):
    monkeypatch.delenv("HERMES_KAKA_HOST_API", raising=False)
    apps = tmp_path / "Applications"
    (apps / "Hermes.app").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    hermes_cli = _executable(bin_dir / "hermes")

    preflight = build_host_shell_pilot_preflight(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command="",
        applications_root=apps,
        home=tmp_path / "home",
        path_env=str(bin_dir),
    )

    assert preflight["host_shell"]["detected"] is True
    app_candidate = preflight["host_shell"]["candidates"][0]
    assert app_candidate["path"] == str(apps / "Hermes.app")
    assert app_candidate["exists"] is True
    cli_candidate = preflight["host_shell"]["cli"]
    assert cli_candidate["path"] == str(hermes_cli)
    assert cli_candidate["found"] is True
    assert preflight["private_adapter_command"]["selected"]["provided"] is False
    assert preflight["status"] == "blocked"
    assert "missing_private_adapter_command" in preflight["release_preflight"]["blocking_reasons"]


def test_preflight_detects_environment_command_without_invoking_it(tmp_path, monkeypatch):
    sentinel = tmp_path / "called.txt"
    command = _executable(
        tmp_path / "hermes-kaka-host-api",
        body=f"#!/bin/sh\ntouch {sentinel}\nexit 0\n",
    )
    monkeypatch.setenv("HERMES_KAKA_HOST_API", str(command))
    apps = tmp_path / "Applications"
    (apps / "Hermes.app").mkdir(parents=True)

    preflight = build_host_shell_pilot_preflight(
        BridgeConfig(runtime="hermes", repo_root=Path.cwd()),
        private_adapter_command="",
        applications_root=apps,
        home=tmp_path / "home",
        path_env="",
    )

    assert sentinel.exists() is False
    assert preflight["ok"] is True
    assert preflight["status"] == "ready_for_conformance"
    assert preflight["private_adapter_command"]["selected"] == {
        "provided": True,
        "source": "environment_variable",
        "path": str(command),
        "exists": True,
        "executable": True,
        "outside_kaka_repo": True,
    }
    assert preflight["private_adapter_command"]["environment_variable"]["name"] == "HERMES_KAKA_HOST_API"
    assert preflight["private_adapter_command"]["environment_variable"]["configured"] is True
    assert preflight["release_preflight"]["can_run_conformance"] is True
    assert preflight["release_preflight"]["can_mark_p3_4_complete"] is False


def test_preflight_reports_path_command_as_informational_only(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCLAW_KAKA_HOST_API", raising=False)
    apps = tmp_path / "Applications"
    (apps / "OpenClaw.app").mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    command = _executable(bin_dir / "openclaw-kaka-host-api")

    preflight = build_host_shell_pilot_preflight(
        BridgeConfig(runtime="openclaw", repo_root=Path.cwd()),
        private_adapter_command="",
        applications_root=apps,
        home=tmp_path / "home",
        path_env=str(bin_dir),
    )

    path_command = preflight["private_adapter_command"]["path_command"]
    assert path_command["found"] is True
    assert path_command["path"] == str(command)
    assert path_command["informational_only"] is True
    assert preflight["private_adapter_command"]["selected"]["provided"] is False
    assert "path_command_not_used_for_pilot_discovery" in preflight["next_actions"]


def test_preflight_detects_manifest_entrypoint_command(tmp_path, monkeypatch):
    monkeypatch.delenv("HERMES_KAKA_HOST_API", raising=False)
    command = _executable(tmp_path / "manifest-hermes-kaka-host-api")
    repo_root = tmp_path / "repo"
    manifest_path = repo_root / "runtime-kit" / "hermes-plugin" / "kaka-mobile-bridge.package.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({
        "host_private_adapter": {
            "command": str(command),
        },
    }))
    apps = tmp_path / "Applications"
    (apps / "Hermes.app").mkdir(parents=True)

    preflight = build_host_shell_pilot_preflight(
        BridgeConfig(runtime="hermes", repo_root=repo_root),
        private_adapter_command="",
        applications_root=apps,
        home=tmp_path / "home",
        path_env="",
    )

    assert preflight["ok"] is True
    assert preflight["private_adapter_command"]["manifest_entrypoint"]["configured"] is True
    assert preflight["private_adapter_command"]["selected"]["source"] == "manifest_entrypoint"
    assert preflight["private_adapter_command"]["selected"]["path"] == str(command)


def test_preflight_detects_well_known_private_adapter_path(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCLAW_KAKA_HOST_API", raising=False)
    home = tmp_path / "home"
    command = _executable(
        home
        / "Library"
        / "Application Support"
        / "OpenClaw"
        / "Kaka"
        / "openclaw-kaka-host-api"
    )
    apps = tmp_path / "Applications"
    (apps / "OpenClaw.app").mkdir(parents=True)

    preflight = build_host_shell_pilot_preflight(
        BridgeConfig(runtime="openclaw", repo_root=Path.cwd()),
        private_adapter_command="",
        applications_root=apps,
        home=home,
        path_env="",
    )

    assert preflight["ok"] is True
    assert preflight["private_adapter_command"]["well_known_paths"][0]["path"] == str(command)
    assert preflight["private_adapter_command"]["well_known_paths"][0]["exists"] is True
    assert preflight["private_adapter_command"]["selected"]["source"] == "well_known_path"


def test_preflight_cli_outputs_machine_readable_report(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCLAW_KAKA_HOST_API", str(_executable(tmp_path / "openclaw-kaka-host-api")))

    exit_code = main([
        "host-shell-pilot-preflight",
        "--runtime",
        "openclaw",
        "--applications-root",
        str(tmp_path / "Applications"),
        "--home",
        str(tmp_path / "home"),
        "--path-env",
        "",
    ])

    preflight = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert preflight["schema_version"] == "kaka.host_shell_pilot_preflight.v1"
    assert preflight["runtime"] == "openclaw"
    assert preflight["private_adapter_command"]["selected"]["source"] == "environment_variable"
    assert preflight["host_shell"]["detected"] is False
    assert preflight["status"] == "blocked"
