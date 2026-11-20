"""Provider keys live in the system keychain when it answers.

Windows uses Credential Manager, macOS the Keychain, Linux Secret Service.
If none of those answer, the keys stay in .env so a machine without a
keyring still runs. A working keychain is preferred, and a saved key is
removed from .env.
"""

from __future__ import annotations

SERVICE = "ulei"

_store: object | None = None
_enabled = False


class MemoryStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, name: str) -> str:
        return self.values.get(name, "")

    def set(self, name: str, value: str) -> None:
        self.values[name] = value

    def delete(self, name: str) -> None:
        self.values.pop(name, None)


class KeyringStore:
    def get(self, name: str) -> str:
        import keyring

        return keyring.get_password(SERVICE, name) or ""

    def set(self, name: str, value: str) -> None:
        import keyring

        keyring.set_password(SERVICE, name, value)

    def delete(self, name: str) -> None:
        import keyring

        try:
            keyring.delete_password(SERVICE, name)
        except Exception:
            return


def use_secret_store(store) -> None:
    global _store, _enabled
    _store = store
    _enabled = store is not None


def active_store():
    return _store if _enabled else None


def redact(text: str, secrets: list[str] | tuple[str, ...]) -> str:
    cleaned = str(text)
    for secret in secrets:
        if secret and len(secret) >= 6 and secret in cleaned:
            cleaned = cleaned.replace(secret, "***")
    return cleaned


def enable_system_keyring() -> bool:
    """Turn the keychain on when a probe succeeds. Safe to call more than once."""
    if _enabled and not isinstance(_store, KeyringStore):
        return True
    try:
        import keyring

        keyring.get_password(SERVICE, "__probe__")
    except Exception:
        return False
    use_secret_store(KeyringStore())
    return True
