"""Shared media-storage test fixtures for the backend suite.

This complements the repo-root ``conftest.py`` (Postgres provisioning, HTTP
clients, session fixtures). It adds the fake object-storage seam introduced by
the migrate-image-storage-to-r2 change (design Decision 8): tests inject an
in-memory ``key -> bytes`` backend instead of hitting a live R2 bucket, so the
suite stays hermetic and needs no credentials.

Two things are wired here:

- ``FakeStorageBackend`` — a tiny in-memory backend (records puts and deletes)
  satisfying ``object_storage_service.StorageBackend``.
- ``fake_storage`` — a fixture that installs a ``FakeStorageBackend`` via
  ``object_storage_service.set_backend`` and points ``r2_public_base_url`` at a
  deterministic test base so uploaded URLs are predictable. It resets the backend
  and the setting on teardown.

Route tests under ``tests/realapp`` reuse ``fake_storage`` too (see
``tests/realapp/conftest.py``), so any real upload path (e.g. the about-image
route) writes to the in-memory backend and produces R2 public URLs.
"""

import pytest

from app.config import get_settings
from app.services import object_storage_service

# Deterministic public base for tests so uploaded URLs are predictable and can be
# reverse-mapped to object keys by slicing off this prefix.
R2_TEST_PUBLIC_BASE = "https://cdn.test.example"


class FakeStorageBackend:
    """In-memory object-storage backend (key -> bytes) for tests; no live bucket.

    Records every stored object and every delete so tests can assert on the exact
    keys written/removed. Set ``fail=True`` to make every operation raise
    ``MediaStorageError`` (used by the Layer-1 isolation test to prove checkout
    survives a storage outage).
    """

    def __init__(self, *, fail: bool = False) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        self.deleted: list[str] = []
        self.fail = fail

    def put_object(self, key: str, data: bytes, content_type: str) -> None:
        if self.fail:
            raise object_storage_service.MediaStorageError("fake storage put failure")
        self.objects[key] = data
        self.content_types[key] = content_type

    def delete_object(self, key: str) -> None:
        if self.fail:
            raise object_storage_service.MediaStorageError("fake storage delete failure")
        self.deleted.append(key)
        self.objects.pop(key, None)
        self.content_types.pop(key, None)


@pytest.fixture()
def fake_storage():
    """Install an in-memory R2 backend and configure the public base URL.

    Yields the backend so tests can assert on stored/deleted object keys. On
    teardown the backend is reset (so the next test falls back to the lazily
    constructed R2 backend, which raises without config) and the public base URL
    is restored.
    """
    settings = get_settings()
    original_base = settings.r2_public_base_url
    settings.r2_public_base_url = R2_TEST_PUBLIC_BASE
    backend = FakeStorageBackend()
    object_storage_service.set_backend(backend)
    try:
        yield backend
    finally:
        object_storage_service.set_backend(None)
        settings.r2_public_base_url = original_base
