"""Handwriting-practice drawings: save, list per word, gallery, delete."""

from __future__ import annotations

import base64
import struct
import zlib

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str) -> str:
    res = client.post("/v1/auth/register", json={"email": email, "password": "supersecret"})
    assert res.status_code == 201
    return res.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _entries(client: TestClient, token: str, quiz: str = "HSK1") -> list[dict]:
    res = client.get(f"/v1/quizzes/{quiz}/entries", headers=_auth(token))
    assert res.status_code == 200
    return res.json()


def _png(width: int = 4, height: int = 2) -> str:
    """A real (tiny, white) PNG as a canvas-style data URL."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    raw = b"".join(b"\x00" + b"\xff" * (width * 3) for _ in range(height))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    return "data:image/png;base64," + base64.b64encode(png).decode()


def test_drawings_require_auth(client: TestClient) -> None:
    assert client.get("/v1/drawings?entry_id=1").status_code in (401, 403)
    assert client.post("/v1/drawings", json={"entry_id": 1, "image": _png()}).status_code in (401, 403)
    assert client.get("/v1/drawings/gallery").status_code in (401, 403)


def test_save_then_list_newest_first(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "draw-save@example.com")
    entry_id = _entries(client, token)[0]["id"]

    first = client.post("/v1/drawings", headers=_auth(token), json={"entry_id": entry_id, "image": _png(4, 2)})
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["entry_id"] == entry_id
    assert (body["width"], body["height"]) == (4, 2)
    assert body["image"] == _png(4, 2)  # round-trips byte for byte

    second = client.post("/v1/drawings", headers=_auth(token), json={"entry_id": entry_id, "image": _png(8, 2)})
    assert second.status_code == 201

    listed = client.get(f"/v1/drawings?entry_id={entry_id}", headers=_auth(token)).json()
    assert [d["id"] for d in listed] == [second.json()["id"], first.json()["id"]]


def test_drawings_are_private(client: TestClient, seed_quizzes) -> None:
    alice = _register(client, "draw-alice@example.com")
    bob = _register(client, "draw-bob@example.com")
    entry_id = _entries(client, alice)[0]["id"]
    drawing = client.post("/v1/drawings", headers=_auth(alice), json={"entry_id": entry_id, "image": _png()}).json()

    assert client.get(f"/v1/drawings?entry_id={entry_id}", headers=_auth(bob)).json() == []
    assert client.get("/v1/drawings/gallery", headers=_auth(bob)).json()["total_drawings"] == 0
    assert client.delete(f"/v1/drawings/{drawing['id']}", headers=_auth(bob)).status_code == 404
    assert len(client.get(f"/v1/drawings?entry_id={entry_id}", headers=_auth(alice)).json()) == 1


def test_rejects_non_png_and_unknown_entry(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "draw-bad@example.com")
    entry_id = _entries(client, token)[0]["id"]
    jpeg = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8" + b"0" * 40).decode()
    fake_png = "data:image/png;base64," + base64.b64encode(b"not a png at all, just text....").decode()

    for image in (jpeg, fake_png, "data:image/png;base64,@@@@not-base64@@@@@@@@@@@@@@@"):
        res = client.post("/v1/drawings", headers=_auth(token), json={"entry_id": entry_id, "image": image})
        assert res.status_code == 422, image

    res = client.post("/v1/drawings", headers=_auth(token), json={"entry_id": 999999, "image": _png()})
    assert res.status_code == 404


def test_gallery_groups_by_word_and_paginates(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "draw-gallery@example.com")
    entries = [_entries(client, token, "HSK1")[0], _entries(client, token, "HSK2")[0]]
    a, b = entries[0]["id"], entries[1]["id"]
    for _ in range(6):
        client.post("/v1/drawings", headers=_auth(token), json={"entry_id": a, "image": _png()})
    client.post("/v1/drawings", headers=_auth(token), json={"entry_id": b, "image": _png()})

    gallery = client.get("/v1/drawings/gallery", headers=_auth(token)).json()
    assert gallery["total_drawings"] == 7
    assert gallery["total_words"] == 2
    assert gallery["has_more"] is False
    # b was drawn last, so it comes first.
    assert [w["entry_id"] for w in gallery["words"]] == [b, a]
    word_a = gallery["words"][1]
    assert word_a["count"] == 6
    assert len(word_a["drawings"]) == 4  # preview only
    assert word_a["hanzi"] == entries[0]["hanzi"]
    assert word_a["hsk_level"] == 1

    page = client.get("/v1/drawings/gallery?limit=1", headers=_auth(token)).json()
    assert [w["entry_id"] for w in page["words"]] == [b]
    assert page["has_more"] is True
    page2 = client.get("/v1/drawings/gallery?limit=1&offset=1", headers=_auth(token)).json()
    assert [w["entry_id"] for w in page2["words"]] == [a]
    assert page2["has_more"] is False


def test_delete(client: TestClient, seed_quizzes) -> None:
    token = _register(client, "draw-delete@example.com")
    entry_id = _entries(client, token)[0]["id"]
    drawing = client.post("/v1/drawings", headers=_auth(token), json={"entry_id": entry_id, "image": _png()}).json()

    assert client.delete(f"/v1/drawings/{drawing['id']}", headers=_auth(token)).status_code == 204
    assert client.get(f"/v1/drawings?entry_id={entry_id}", headers=_auth(token)).json() == []
    assert client.delete(f"/v1/drawings/{drawing['id']}", headers=_auth(token)).status_code == 404


def test_per_user_limit(client: TestClient, seed_quizzes, monkeypatch) -> None:
    from app.services import drawing_service

    monkeypatch.setattr(drawing_service, "MAX_DRAWINGS_PER_USER", 2)
    token = _register(client, "draw-limit@example.com")
    entry_id = _entries(client, token)[0]["id"]
    for _ in range(2):
        assert client.post("/v1/drawings", headers=_auth(token), json={"entry_id": entry_id, "image": _png()}).status_code == 201
    res = client.post("/v1/drawings", headers=_auth(token), json={"entry_id": entry_id, "image": _png()})
    assert res.status_code == 409
    assert "Limite" in res.json()["detail"]
