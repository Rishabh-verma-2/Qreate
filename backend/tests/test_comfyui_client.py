"""Unit tests for ComfyUI workflow templating and client logic."""

import pytest
from app.services.video.comfyui_client import _fill_template, _load_workflow, ComfyUIClient


def test_fill_template():
    """Verify template placeholder replacement."""
    template = {
        "node_1": {
            "prompt": "{{PROMPT}}",
            "width": "{{WIDTH}}",
            "height": "{{HEIGHT}}",
        }
    }
    params = {
        "PROMPT": "A glowing nebula in deep space",
        "WIDTH": "1280",
        "HEIGHT": "720",
    }
    result = _fill_template(template, params)
    assert result["node_1"]["prompt"] == "A glowing nebula in deep space"
    assert result["node_1"]["width"] == "1280"
    assert result["node_1"]["height"] == "720"


def test_load_workflow_templates():
    """Verify that both wan_t2v.json and wan_i2v.json templates load correctly."""
    t2v = _load_workflow("wan_t2v.json")
    assert isinstance(t2v, dict)
    assert "_comment" in t2v

    i2v = _load_workflow("wan_i2v.json")
    assert isinstance(i2v, dict)
    assert "_comment" in i2v


def test_comfyui_client_init():
    """Verify ComfyUIClient initialization."""
    client = ComfyUIClient()
    assert client.base_url.startswith("http")
