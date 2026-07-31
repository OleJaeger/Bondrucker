"""Template configuration loading and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.exceptions import TemplateNotFoundError
from app.templates.loader import TemplateRegistry
from app.templates.schema import LayoutConfig, TemplateConfig


def test_registry_loads_shipped_templates(settings_env):
    registry = TemplateRegistry(settings_env.templates_dir)

    freitext = registry.get("freitext")
    assert freitext.name == "Freitext"
    assert freitext.type == "freitext"
    assert freitext.icon is None

    todo = registry.get("todo")
    assert todo.name == "Aufgabenliste"
    assert todo.type == "todo"
    assert todo.icon == "fa-list-check"

    gemaelde = registry.get("gemaelde")
    assert gemaelde.name == "Gemälde"
    assert gemaelde.type == "gemaelde"
    assert gemaelde.icon == "fa-paintbrush"
    assert gemaelde.fields.markdown is False
    assert gemaelde.fields.attachment is False
    assert gemaelde.default_markdown


def test_registry_lists_all_templates(settings_env):
    registry = TemplateRegistry(settings_env.templates_dir)
    keys = {config.key for config in registry.list()}
    assert keys == {"freitext", "message", "todo", "gemaelde"}


def test_get_unknown_template_raises(settings_env):
    registry = TemplateRegistry(settings_env.templates_dir)
    with pytest.raises(TemplateNotFoundError):
        registry.get("does-not-exist")


def test_invalid_yaml_files_are_skipped(tmp_path):
    (tmp_path / "broken.yaml").write_text("not: valid: yaml: at: all:\n  - [", encoding="utf-8")
    (tmp_path / "missing-fields.yaml").write_text("name: ''\ntype: ''\n", encoding="utf-8")
    (tmp_path / "good.yaml").write_text("name: Gut\ntype: freitext\n", encoding="utf-8")

    registry = TemplateRegistry(tmp_path)

    assert registry.list() == [registry.get("good")]
    with pytest.raises(TemplateNotFoundError):
        registry.get("broken")
    with pytest.raises(TemplateNotFoundError):
        registry.get("missing-fields")


def test_missing_templates_dir_yields_empty_registry(tmp_path):
    registry = TemplateRegistry(tmp_path / "does-not-exist")
    assert registry.list() == []


def test_registry_loads_templates_from_custom_subdir(tmp_path):
    (tmp_path / "good.yaml").write_text("name: Gut\ntype: freitext\n", encoding="utf-8")
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "personal.yaml").write_text("name: Persoenlich\ntype: freitext\n", encoding="utf-8")

    registry = TemplateRegistry(tmp_path)

    keys = {config.key for config in registry.list()}
    assert keys == {"good", "personal"}
    assert registry.get("personal").name == "Persoenlich"


def test_registry_custom_subdir_overrides_same_key(tmp_path):
    (tmp_path / "shared.yaml").write_text("name: Original\ntype: freitext\n", encoding="utf-8")
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "shared.yaml").write_text("name: Ueberschrieben\ntype: freitext\n", encoding="utf-8")

    registry = TemplateRegistry(tmp_path)

    assert registry.get("shared").name == "Ueberschrieben"


def test_template_config_rejects_blank_name_and_type():
    with pytest.raises(ValidationError):
        TemplateConfig(key="x", name="", type="freitext")
    with pytest.raises(ValidationError):
        TemplateConfig(key="x", name="X", type="   ")


@pytest.mark.parametrize("field, value", [("width_chars", 0), ("width_chars", 200), ("feed_lines", -1), ("feed_lines", 21)])
def test_layout_config_rejects_out_of_range_values(field, value):
    with pytest.raises(ValidationError):
        LayoutConfig(**{field: value})
