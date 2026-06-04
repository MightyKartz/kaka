import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from PIL import Image


def load_recipe_adapter():
    adapter_path = Path(__file__).resolve().parents[1] / "adapters" / "recipe_local.py"
    spec = importlib.util.spec_from_file_location("photo_pack_recipe_local_adapter", adapter_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_fixture_photo(path: Path) -> None:
    image = Image.new("RGB", (160, 120), (38, 62, 74))
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            pixels[x, y] = (
                min(255, 34 + x // 2),
                min(255, 58 + y),
                min(255, 82 + (x + y) // 4),
            )
    image.save(path, format="JPEG", quality=92)


def test_recipe_local_adapter_renders_master_and_social_variants(tmp_path):
    adapter = load_recipe_adapter()
    input_path = tmp_path / "input.jpg"
    output_dir = tmp_path / "out"
    write_fixture_photo(input_path)
    source_bytes = input_path.read_bytes()

    result = adapter.run_edit(
        input_path=input_path,
        output_dir=output_dir,
        style="natural_enhance",
        instruction="Keep it realistic but make the professional edit obvious.",
        return_variants=2,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    variants = result["variants"]
    output_paths = [Path(variant["path"]) for variant in variants]

    assert result["status"] == "completed"
    assert result["provider"] == "recipe_local"
    assert result["renderer"] == "local_parametric"
    assert [variant["id"] for variant in variants] == ["variant_clean_pro", "variant_social_pop"]
    assert [variant["label"] for variant in variants] == ["Master", "Social"]
    assert output_paths[0].exists()
    assert output_paths[1].exists()
    assert output_paths[0].read_bytes() != source_bytes
    assert output_paths[1].read_bytes() != source_bytes
    assert output_paths[0].read_bytes() != output_paths[1].read_bytes()
    assert manifest["composition"]["selected_aspect_ratio"] == "original"
    assert manifest["composition"]["crop"] == {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
    assert manifest["qa"]["master_difference_score"] > 0.01
    assert manifest["qa"]["social_difference_score"] > manifest["qa"]["master_difference_score"]
    assert manifest["safety"]["no_generative_pixels"] is True
    assert manifest["share_caption"]


def test_recipe_local_adapter_clamps_recipe_values():
    adapter = load_recipe_adapter()
    recipe = adapter.build_fixture_recipe("natural_enhance", variant_id="variant_clean_pro")
    recipe["global"]["exposure"] = 8.5
    recipe["global"]["temperature"] = -5000
    recipe["local"]["sharpen"] = 99
    recipe["composition"]["crop"] = {"x": -2, "y": 1.4, "width": 3, "height": 0}
    recipe["upscale"]["max_scale"] = 10

    clamped = adapter.validate_recipe(recipe)

    assert clamped["global"]["exposure"] == 1.0
    assert clamped["global"]["temperature"] == -1500
    assert clamped["local"]["sharpen"] == 1.0
    assert clamped["composition"]["crop"] == {"x": 0.0, "y": 0.95, "width": 1.0, "height": 0.05}
    assert clamped["upscale"]["max_scale"] == 3.0


def test_recipe_local_adapter_preserves_original_dimensions_by_default(tmp_path):
    adapter = load_recipe_adapter()
    input_path = tmp_path / "input.jpg"
    output_dir = tmp_path / "out"
    write_fixture_photo(input_path)

    result = adapter.run_edit(
        input_path=input_path,
        output_dir=output_dir,
        style="natural_enhance",
        instruction="Keep it realistic but make the professional edit obvious.",
        return_variants=1,
    )

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    rendered = Image.open(result["variants"][0]["path"])

    assert rendered.size == (160, 120)
    assert manifest["upscale"]["upscaled"] is False
    assert manifest["upscale"]["scale"] == 1.0
    assert manifest["upscale"]["input_size"] == [160, 120]
    assert manifest["upscale"]["output_size"] == [160, 120]


def test_recipe_local_adapter_rejects_missing_safety_flag():
    adapter = load_recipe_adapter()
    recipe = adapter.build_fixture_recipe("portrait_polish", variant_id="variant_clean_pro")
    del recipe["safety"]["preserve_identity"]

    with pytest.raises(adapter.RecipeValidationError, match="preserve_identity"):
        adapter.validate_recipe(recipe)


def test_recipe_local_adapter_rejects_unknown_style(tmp_path):
    adapter = load_recipe_adapter()
    input_path = tmp_path / "input.jpg"
    write_fixture_photo(input_path)

    with pytest.raises(ValueError, match="unknown_style"):
        adapter.run_edit(
            input_path=input_path,
            output_dir=tmp_path / "out",
            style="unknown_style",
            instruction="Nope.",
        )


def test_recipe_local_adapter_runtime_vision_posts_photo_context_and_renders_returned_recipe(tmp_path):
    adapter = load_recipe_adapter()
    input_path = tmp_path / "input.jpg"
    output_dir = tmp_path / "out"
    write_fixture_photo(input_path)
    observations: list[dict] = []

    class RuntimeRecipeHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            observations.append(payload)
            recipe = adapter.build_fixture_recipe(payload["style"], variant_id=payload["variant_id"])
            recipe["global"]["exposure"] = 0.22
            body = json.dumps({"recipe": recipe, "model": "runtime-configured-vision"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), RuntimeRecipeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = adapter.run_edit(
            input_path=input_path,
            output_dir=output_dir,
            style="natural_enhance",
            instruction="Use runtime vision.",
            return_variants=1,
            recipe_mode="runtime_vision",
            runtime_recipe_endpoint=f"http://127.0.0.1:{server.server_port}/recipe",
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert result["status"] == "completed"
    assert result["recipe_mode"] == "runtime_vision"
    assert manifest["recipe_model"] == "runtime-configured-vision"
    assert observations
    assert observations[0]["provider"] == "recipe_local"
    assert observations[0]["renderer"] == "local_parametric"
    assert observations[0]["style"] == "natural_enhance"
    assert observations[0]["variant_id"] == "variant_clean_pro"
    assert observations[0]["instruction"] == "Use runtime vision."
    assert observations[0]["scene_profile"]["scene"] == "natural"
    assert observations[0]["scene_profile"]["default_recipe"]["global"]["shadows"] > 0
    assert observations[0]["scene_profile"]["default_recipe"]["local"]["subject_boost"] > 0
    assert "realistic exposure" in observations[0]["scene_profile"]["goal"]
    assert observations[0]["source_image_base64"]
    assert "api_key" not in json.dumps(observations[0]).lower()


def test_recipe_local_adapter_runtime_vision_rejects_invalid_runtime_recipe(tmp_path):
    adapter = load_recipe_adapter()
    input_path = tmp_path / "input.jpg"
    output_dir = tmp_path / "out"
    write_fixture_photo(input_path)

    class RuntimeRecipeHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.dumps({"recipe": {"schema_version": "bad"}}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), RuntimeRecipeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(adapter.RecipeValidationError, match="schema_version"):
            adapter.run_edit(
                input_path=input_path,
                output_dir=output_dir,
                style="natural_enhance",
                instruction="Use runtime vision.",
                recipe_mode="runtime_vision",
                runtime_recipe_endpoint=f"http://127.0.0.1:{server.server_port}/recipe",
            )
    finally:
        server.shutdown()
        thread.join(timeout=2)
