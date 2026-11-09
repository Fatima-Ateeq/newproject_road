from tests.conftest import JPEG_BYTES, PNG_BYTES


def _detail(client, headers, code):
    return client.get(f"/api/admin/complaints/{code}", headers=headers).json()


def test_png_and_jpeg_photos_are_accepted(client, submit, admin_headers):
    for name, content, mime in [("a.png", PNG_BYTES, "image/png"), ("b.jpg", JPEG_BYTES, "image/jpeg")]:
        response = submit(photo=(name, content, mime))
        assert response.status_code == 201
        assert _detail(client, admin_headers, response.json()["complaint_id"])["has_photo"] is True


def test_complaint_without_photo_is_accepted(client, submit, admin_headers):
    code = submit().json()["complaint_id"]
    assert _detail(client, admin_headers, code)["has_photo"] is False


def test_file_that_is_not_an_image_is_rejected_even_with_image_name(submit):
    response = submit(photo=("fake.png", b"this is plain text, not an image", "image/png"))
    assert response.status_code == 422


def test_oversized_photo_is_rejected(submit):
    response = submit(photo=("big.png", PNG_BYTES + b"0" * 5000, "image/png"))
    assert response.status_code == 422
    assert "too large" in response.json()["detail"]


def test_rejected_photo_does_not_create_a_complaint(client, submit, admin_headers):
    submit(photo=("fake.png", b"not an image", "image/png"))
    page = client.get("/api/admin/complaints", headers=admin_headers).json()
    assert page["total"] == 0


def test_admin_can_download_the_photo(client, submit, admin_headers):
    code = submit(photo=("a.png", PNG_BYTES, "image/png")).json()["complaint_id"]
    response = client.get(f"/api/admin/complaints/{code}/photo", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG_BYTES


def test_photo_endpoint_gives_404_when_there_is_no_photo(client, submit, admin_headers):
    code = submit().json()["complaint_id"]
    assert client.get(f"/api/admin/complaints/{code}/photo", headers=admin_headers).status_code == 404
