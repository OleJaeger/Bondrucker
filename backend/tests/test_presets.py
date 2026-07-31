"""Preset (Standarddruckobjekt) configuration loading and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.exceptions import PresetNotFoundError
from app.presets.loader import PresetRegistry
from app.presets.schema import PresetAttachment, PresetConfig


def test_registry_loads_shipped_presets(settings_env):
    registry = PresetRegistry(settings_env.presets_dir)

    wlan = registry.get("wlan-qrcode")
    assert wlan.name == "WLAN-Zugang"
    assert wlan.icon == "fa-wifi"
    assert wlan.template == "message"
    assert wlan.category == "Information"
    assert wlan.content_script is None
    assert wlan.attachment is not None
    assert wlan.attachment.type == "qr_code"
    assert wlan.attachment.content is not None

    positive = registry.get("positive-nachricht")
    assert positive.name == "Positive Nachricht"
    assert positive.icon == "fa-heart"
    assert positive.template == "message"
    assert positive.content_script == "positive_message"

    tasks = registry.get("heutige-aufgaben")
    assert tasks.icon == "fa-list-check"
    assert tasks.template == "todo"
    assert tasks.content_script == "super_productivity_today"

    shopping = registry.get("einkaufsliste")
    assert shopping.icon == "fa-cart-shopping"
    assert shopping.template == "todo"
    assert shopping.content_script == "mealie_shopping_list"

    mealplan = registry.get("essenplan-woche")
    assert mealplan.icon == "fa-calendar-week"
    assert mealplan.template == "freitext"
    assert mealplan.content_script == "mealie_mealplan"

    weather = registry.get("wettervorhersage")
    assert weather.icon == "fa-cloud-sun"
    assert weather.template == "freitext"
    assert weather.content_script == "weather_forecast"

    tenets = registry.get("tenets-of-it")
    assert tenets.name == "Grundsätze der IT"
    assert tenets.icon == "fa-server"
    assert tenets.template == "message"
    assert tenets.content_script == "tenets_of_it"

    ausmalbild = registry.get("ausmalbild")
    assert ausmalbild.name == "Ausmalbild"
    assert ausmalbild.icon == "fa-paw"
    assert ausmalbild.template == "gemaelde"
    assert ausmalbild.attachment is not None
    assert ausmalbild.attachment.type == "image"
    assert ausmalbild.attachment.script == "random_animal"

    recipe = registry.get("rezept-heute")
    assert recipe.icon == "fa-utensils"
    assert recipe.template == "freitext"
    assert recipe.content_script == "mealie_recipe_today"
    assert recipe.attachment is not None
    assert recipe.attachment.type == "image"
    assert recipe.attachment.script == "mealie_recipe_today"

    news = registry.get("news-wichtig")
    assert news.icon == "fa-newspaper"
    assert news.template == "freitext"
    assert news.content_script == "news_important"


def test_registry_lists_all_presets(settings_env):
    registry = PresetRegistry(settings_env.presets_dir)
    keys = {config.key for config in registry.list()}
    assert keys == {
        "wlan-qrcode",
        "positive-nachricht",
        "heutige-aufgaben",
        "einkaufsliste",
        "essenplan-woche",
        "wettervorhersage",
        "tenets-of-it",
        "jagdtag-heute",
        "fridge-art",
        "ausmalbild",
        "rezept-heute",
        "news-wichtig",
    }


def test_get_unknown_preset_raises(settings_env):
    registry = PresetRegistry(settings_env.presets_dir)
    with pytest.raises(PresetNotFoundError):
        registry.get("does-not-exist")


def test_invalid_yaml_files_are_skipped(tmp_path):
    (tmp_path / "broken.yaml").write_text("not: valid: yaml: at: all:\n  - [", encoding="utf-8")
    (tmp_path / "missing-fields.yaml").write_text("name: ''\ndescription: ''\nicon: ''\ntemplate: ''\n", encoding="utf-8")
    (tmp_path / "good.yaml").write_text(
        "name: Gut\ndescription: Ein gutes Preset\nicon: fa-star\ntemplate: freitext\n", encoding="utf-8"
    )

    registry = PresetRegistry(tmp_path)

    assert registry.list() == [registry.get("good")]
    with pytest.raises(PresetNotFoundError):
        registry.get("broken")
    with pytest.raises(PresetNotFoundError):
        registry.get("missing-fields")


def test_missing_presets_dir_yields_empty_registry(tmp_path):
    registry = PresetRegistry(tmp_path / "does-not-exist")
    assert registry.list() == []


def test_registry_loads_presets_from_custom_subdir(tmp_path):
    (tmp_path / "good.yaml").write_text(
        "name: Gut\ndescription: Ein gutes Preset\nicon: fa-star\ntemplate: freitext\n", encoding="utf-8"
    )
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "personal.yaml").write_text(
        "name: Persoenlich\ndescription: Mein Preset\nicon: fa-star\ntemplate: freitext\n", encoding="utf-8"
    )

    registry = PresetRegistry(tmp_path)

    keys = {config.key for config in registry.list()}
    assert keys == {"good", "personal"}
    assert registry.get("personal").name == "Persoenlich"


def test_registry_custom_subdir_overrides_same_key(tmp_path):
    (tmp_path / "shared.yaml").write_text(
        "name: Original\ndescription: Original\nicon: fa-star\ntemplate: freitext\n", encoding="utf-8"
    )
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "shared.yaml").write_text(
        "name: Ueberschrieben\ndescription: Ueberschrieben\nicon: fa-star\ntemplate: freitext\n", encoding="utf-8"
    )

    registry = PresetRegistry(tmp_path)

    assert registry.get("shared").name == "Ueberschrieben"


@pytest.mark.parametrize("field", ["name", "description", "icon", "template", "category"])
def test_preset_config_rejects_blank_required_fields(field):
    values = {"key": "x", "name": "X", "description": "Y", "icon": "fa-star", "template": "freitext"}
    values[field] = "   "
    with pytest.raises(ValidationError):
        PresetConfig(**values)


def test_preset_config_category_defaults_to_sonstige():
    config = PresetConfig(key="x", name="X", description="Y", icon="fa-star", template="freitext")
    assert config.category == "Sonstige"


def test_preset_config_keys_defaults_to_empty_list():
    config = PresetConfig(key="x", name="X", description="Y", icon="fa-star", template="freitext")
    assert config.config_keys == []


def test_preset_config_rejects_unknown_config_keys():
    with pytest.raises(ValidationError):
        PresetConfig(
            key="x",
            name="X",
            description="Y",
            icon="fa-star",
            template="freitext",
            config_keys=["not_a_real_settings_field"],
        )


def test_einkaufsliste_registers_mealie_config_keys(settings_env):
    registry = PresetRegistry(settings_env.presets_dir)
    shopping = registry.get("einkaufsliste")
    assert shopping.config_keys == ["mealie_base_url", "mealie_api_token", "mealie_shopping_list_id"]


def test_essenplan_woche_registers_mealie_config_keys(settings_env):
    registry = PresetRegistry(settings_env.presets_dir)
    mealplan = registry.get("essenplan-woche")
    assert mealplan.config_keys == ["mealie_base_url", "mealie_api_token"]


def test_news_wichtig_registers_news_config_keys(settings_env):
    registry = PresetRegistry(settings_env.presets_dir)
    news = registry.get("news-wichtig")
    assert news.config_keys == [
        "news_base_url",
        "news_authentik_token_url",
        "news_client_id",
        "news_authentik_username",
        "news_authentik_password",
    ]


def test_rezept_heute_registers_mealie_config_keys(settings_env):
    registry = PresetRegistry(settings_env.presets_dir)
    recipe = registry.get("rezept-heute")
    assert recipe.config_keys == ["mealie_base_url", "mealie_api_token"]


def test_preset_config_content_and_content_script_are_exclusive():
    with pytest.raises(ValidationError):
        PresetConfig(
            key="x",
            name="X",
            description="Y",
            icon="fa-star",
            template="freitext",
            content="Hallo",
            content_script="positive_message",
        )


@pytest.mark.parametrize("name", ["Invalid", "1bad", "bad-name", "bad name", ""])
def test_preset_config_rejects_invalid_content_script_names(name):
    with pytest.raises(ValidationError):
        PresetConfig(
            key="x",
            name="X",
            description="Y",
            icon="fa-star",
            template="freitext",
            content_script=name,
        )


def test_preset_attachment_qr_code_requires_content():
    with pytest.raises(ValidationError):
        PresetAttachment(type="qr_code")

    attachment = PresetAttachment(type="qr_code", content="https://example.com")
    assert attachment.content == "https://example.com"


def test_preset_attachment_image_requires_exactly_one_of_path_or_script():
    with pytest.raises(ValidationError):
        PresetAttachment(type="image")

    with pytest.raises(ValidationError):
        PresetAttachment(type="image", path="logo.png", script="random_animal")

    attachment = PresetAttachment(type="image", path="logo.png")
    assert attachment.path == "logo.png"

    attachment = PresetAttachment(type="image", script="random_animal")
    assert attachment.script == "random_animal"


@pytest.mark.parametrize("name", ["Invalid", "1bad", "bad-name", "bad name"])
def test_preset_attachment_rejects_invalid_script_names(name):
    with pytest.raises(ValidationError):
        PresetAttachment(type="image", script=name)
