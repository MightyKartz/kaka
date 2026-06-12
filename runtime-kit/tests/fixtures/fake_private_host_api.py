from __future__ import annotations

import argparse
import json
import sys
import time


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--invalid-json", action="store_true")
    parser.add_argument("--invalid-schema", action="store_true")
    parser.add_argument("--extra-secret", action="store_true")
    parser.add_argument("--fail", action="store_true")
    parser.add_argument("--sleep", type=float, default=0)
    args = parser.parse_args(argv)

    if args.sleep > 0:
        time.sleep(args.sleep)
    if args.invalid_json:
        print("not-json")
        return 0
    if args.invalid_schema:
        print(json.dumps({"schema_version": "wrong", "ok": True}))
        return 0
    if args.fail:
        print(json.dumps({"error": {"code": "fake_failure", "message": "fake command failed"}}))
        return 3

    request = json.loads(sys.stdin.read())
    action_id = request["action_id"]
    state = dict(request["state"])
    mutated = False
    if action_id == "install_runtime_package":
        state.update({
            "installed": True,
            "start_with_runtime": False,
            "process_state": "stopped",
            "process_supervision": "not_configured",
            "health_status": "unknown",
            "port_conflict": False,
        })
        mutated = True
    elif action_id == "enable_start_with_runtime":
        state["start_with_runtime"] = True
        mutated = True
    elif action_id == "disable_start_with_runtime":
        state["start_with_runtime"] = False
        mutated = True
    elif action_id == "update_runtime_package":
        state["installed"] = True
        mutated = True
    elif action_id == "uninstall_runtime_package":
        state.update({
            "installed": False,
            "start_with_runtime": False,
            "process_state": "stopped",
            "process_supervision": "not_configured",
            "health_status": "unknown",
            "port_conflict": False,
        })
        mutated = True
    elif action_id == "open_runtime_logs":
        state["health_status"] = state.get("health_status", "unknown")
    elif action_id == "run_health_check":
        state["health_status"] = "healthy"
    elif action_id == "repair_port_conflict":
        state["port_conflict"] = False
        mutated = True
    elif action_id == "supervise_bridge":
        state["process_supervision"] = "host_managed"
        mutated = True

    response = {
        "schema_version": "kaka.host_private_adapter_response.v1",
        "ok": True,
        "mutated_host_state": mutated,
        "state": state,
        "detail": {
            "private_api_called": True,
            "private_api_provider": "fake_private_host_api",
            "host_api_level": "test_fixture",
        },
    }
    if args.extra_secret:
        response["raw_secret"] = "do not forward"
        response["detail"]["secret_log_path"] = "/private/log"

    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
