"""Qt desktop presentation, imported lazily for headless tooling."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .guided_window import EditorWindow

__all__ = ["EditorWindow"]


def __getattr__(name: str) -> object:
    if name == "EditorWindow":
        from .guided_window import EditorWindow

        return EditorWindow
    raise AttributeError(name)
