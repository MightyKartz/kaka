import importlib.util
import json
from pathlib import Path


def load_script_adapter():
    adapter_path = Path(__file__).resolve().parents[1] / "adapters" / "script.py"
    spec = importlib.util.spec_from_file_location("photo_pack_script_adapter", adapter_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_adapter_creates_deterministic_variant(tmp_path):
    adapter = load_script_adapter()
    input_path = tmp_path / "input.jpg"
    output_dir = tmp_path / "out"
    input_path.write_bytes(b"source-image")

    result = adapter.run_edit(
        input_path=input_path,
        output_dir=output_dir,
        style="natural_enhance",
        instruction="Keep it realistic.",
    )

    output_path = Path(result["variants"][0]["path"])
    manifest_path = output_dir / "manifest.json"

    assert result["status"] == "completed"
    assert output_path.exists()
    assert output_path.read_bytes() == b"source-image"
    assert result["variants"][0]["label"] == "Natural Enhance"
    assert json.loads(manifest_path.read_text())["style"] == "natural_enhance"


def test_script_adapter_rejects_unknown_style(tmp_path):
    adapter = load_script_adapter()
    input_path = tmp_path / "input.jpg"
    input_path.write_bytes(b"source-image")

    try:
        adapter.run_edit(
            input_path=input_path,
            output_dir=tmp_path / "out",
            style="unknown_style",
            instruction="Nope.",
        )
    except ValueError as error:
        assert "unknown_style" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_script_adapter_cli_writes_json_to_stdout(tmp_path, capsys):
    adapter = load_script_adapter()
    input_path = tmp_path / "input.jpg"
    output_dir = tmp_path / "out"
    input_path.write_bytes(b"source-image")

    exit_code = adapter.main(
        [
            "--input",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--style",
            "social_cover",
            "--instruction",
            "Make it title-safe.",
        ]
    )

    stdout = capsys.readouterr().out
    payload = json.loads(stdout)

    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["variants"][0]["label"] == "Social Cover"
