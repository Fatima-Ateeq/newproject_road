import re


def test_submit_returns_a_complaint_id(submit):
    response = submit()
    assert response.status_code == 201
    assert re.fullmatch(r"RW-\d{4}-000001", response.json()["complaint_id"])


def test_ids_are_unique_and_sequential(submit):
    first = submit().json()["complaint_id"]
    second = submit().json()["complaint_id"]
    assert first != second
    assert second.endswith("000002")


def test_tracking_shows_pending_status_and_timeline(client, submit):
    code = submit().json()["complaint_id"]
    body = client.get(f"/api/complaints/{code}").json()
    assert body["complaint_id"] == code
    assert body["status"] == "Pending"
    assert [entry["status"] for entry in body["timeline"]] == ["Pending"]


def test_tracking_never_reveals_private_details(client, submit):
    code = submit(contact="0300-1234567", address_text="Mall Road").json()["complaint_id"]
    body = client.get(f"/api/complaints/{code}").json()
    for private_field in ("contact", "latitude", "longitude", "address_text", "description"):
        assert private_field not in body


def test_unknown_or_malformed_code_gives_404(client):
    assert client.get("/api/complaints/RW-2026-999999").status_code == 404
    assert client.get("/api/complaints/not-a-code").status_code == 404


def test_description_must_be_at_least_ten_characters(submit):
    assert submit(description="too short").status_code == 422


def test_coordinates_must_be_valid(submit):
    assert submit(latitude="95").status_code == 422
    assert submit(longitude="-181").status_code == 422


def test_blank_optional_fields_are_stored_as_empty(client, submit, admin_headers):
    code = submit(contact="   ", address_text="").json()["complaint_id"]
    detail = client.get(f"/api/admin/complaints/{code}", headers=admin_headers).json()
    assert detail["contact"] is None
    assert detail["address_text"] is None
