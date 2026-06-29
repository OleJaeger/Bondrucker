"""Application-level exceptions, mapped to HTTP responses in ``main.py``."""

from __future__ import annotations


class AppError(Exception):
    """Base class for all application errors that map to an HTTP response."""


class TemplateNotFoundError(AppError):
    """Raised when a job references a template that does not exist."""

    def __init__(self, template: str):
        self.template = template
        super().__init__(f"Unbekannte Druckvorlage: {template!r}")


class InvalidTemplateConfigError(AppError):
    """Raised when a template YAML file fails schema validation."""

    def __init__(self, path: str, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Ungueltige Vorlagenkonfiguration {path!r}: {reason}")


class InvalidMarkdownError(AppError):
    """Raised when the submitted markdown cannot be parsed/rendered."""


class InvalidAttachmentError(AppError):
    """Raised when an uploaded image or QR-code payload is invalid."""


class JobNotFoundError(AppError):
    """Raised when a print job id does not exist."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Druckauftrag nicht gefunden: {job_id}")


class InvalidJobStateError(AppError):
    """Raised on illegal job state transitions (e.g. cancel of a printing job)."""


class PrinterOfflineError(AppError):
    """Raised when the printer cannot be reached over the network."""


class PrinterCommandError(AppError):
    """Raised when the printer rejects/aborts a print job."""


class IconRenderError(AppError):
    """Raised internally when an icon cannot be rendered; always caught and
    degraded gracefully by the rendering pipeline, never surfaced via the API."""


class PresetNotFoundError(AppError):
    """Raised when a print job references a preset (Standarddruckobjekt) that does not exist."""

    def __init__(self, preset: str):
        self.preset = preset
        super().__init__(f"Unbekanntes Standarddruckobjekt: {preset!r}")


class PresetScriptError(AppError):
    """Raised when a preset's content script fails or an external dependency
    (Mealie, Open-Meteo, Super Productivity) cannot be reached."""
