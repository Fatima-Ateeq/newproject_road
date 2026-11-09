from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models import Complaint


def _patch(client, headers, code, **changes):
    return client.patch(f"/api/admin/complaints/{code}", json=changes, headers=headers)


def test_list_is_newest_first_with_paging(client, submit, admin_headers):
    codes = [submit().json()["complaint_id"] for _ in range(3)]
    page = client.get("/api/admin/complaints?page=1&page_size=2", headers=admin_headers).json()
    assert page["total"] == 3
    assert [item["complaint_id"] for item in page["items"]] == [codes[2], codes[1]]
    second = client.get("/api/admin/complaints?page=2&page_size=2", headers=admin_headers).json()
    assert [item["complaint_id"] for item in second["items"]] == [codes[0]]


def test_list_filters_by_status_category_and_priority(client, submit, admin_headers):
    first = submit().json()["complaint_id"]
    submit()
    _patch(client, admin_headers, first, status="In Progress", category="Road Damage", priority="High")

    def total(query: str) -> int:
        return client.get(f"/api/admin/complaints?{query}", headers=admin_headers).json()["total"]

    assert total("status=In Progress") == 1
    assert total("category=Road Damage") == 1
    assert total("priority=High") == 1
    assert total("status=Pending") == 1
    assert total("category=Other") == 0


def test_list_search_matches_description_and_address(client, submit, admin_headers):
    submit(description="Broken railway gate near the station.")
    submit(address_text="Canal Road")
    search = lambda text: client.get(f"/api/admin/complaints?search={text}", headers=admin_headers).json()["total"]
    assert search("railway") == 1
    assert search("canal") == 1
    assert search("nothing-matches") == 0


def test_list_filters_by_date(client, submit, admin_headers, settings):
    submit()
    today = datetime.now(ZoneInfo(settings.timezone)).date()    # "today" as the administrator sees it
    tomorrow = today + timedelta(days=1)
    total = lambda query: client.get(f"/api/admin/complaints?{query}", headers=admin_headers).json()["total"]
    assert total(f"date_from={today}") == 1
    assert total(f"date_from={tomorrow}") == 0
    assert total(f"date_to={today}") == 1


def test_detail_includes_private_fields(client, submit, admin_headers):
    code = submit(contact="0300-1234567", address_text="Mall Road").json()["complaint_id"]
    detail = client.get(f"/api/admin/complaints/{code}", headers=admin_headers).json()
    assert detail["contact"] == "0300-1234567"
    assert detail["address_text"] == "Mall Road"
    assert detail["latitude"] == 31.5204


def test_status_change_is_recorded_and_visible_to_the_citizen(client, submit, admin_headers):
    code = submit().json()["complaint_id"]
    response = _patch(client, admin_headers, code, status="Under Review", action_note="Inspection scheduled")
    assert response.status_code == 200

    history = response.json()["history"]
    assert [entry["new_status"] for entry in history] == ["Pending", "Under Review"]
    assert history[1]["old_status"] == "Pending"
    assert history[1]["changed_by"] == "admin"

    tracked = client.get(f"/api/complaints/{code}").json()
    assert tracked["status"] == "Under Review"
    assert tracked["timeline"][-1]["note"] == "Inspection scheduled"
    assert "changed_by" not in tracked["timeline"][-1]


def test_note_without_status_change_is_still_recorded(client, submit, admin_headers):
    code = submit().json()["complaint_id"]
    history = _patch(client, admin_headers, code, action_note="Contacted the contractor").json()["history"]
    assert len(history) == 2
    assert history[1]["old_status"] == history[1]["new_status"] == "Pending"


def test_category_or_priority_change_alone_adds_no_history(client, submit, admin_headers):
    code = submit().json()["complaint_id"]
    detail = _patch(client, admin_headers, code, category="Other", priority="Low").json()
    assert detail["category"] == "Other"
    assert detail["priority"] == "Low"
    assert len(detail["history"]) == 1


def test_update_must_change_something(client, submit, admin_headers):
    code = submit().json()["complaint_id"]
    assert _patch(client, admin_headers, code).status_code == 422


def test_update_rejects_unknown_status(client, submit, admin_headers):
    code = submit().json()["complaint_id"]
    assert _patch(client, admin_headers, code, status="Finished").status_code == 422


def test_updating_an_unknown_complaint_gives_404(client, admin_headers):
    assert _patch(client, admin_headers, "RW-2026-999999", status="Resolved").status_code == 404


def test_date_filters_use_the_administrators_local_day_not_utc(client, session_factory, admin_headers):
    """A complaint made at 02:00 on 3 November in Pakistan is stored as 21:00 UTC on 2 November."""
    with session_factory() as db:
        db.add(Complaint(description="Pothole filed just after local midnight", latitude=31.5, longitude=74.3,
                         created_at=datetime(2026, 11, 2, 21, 0, tzinfo=timezone.utc)))
        db.commit()

    def total(query: str) -> int:
        return client.get(f"/api/admin/complaints?{query}", headers=admin_headers).json()["total"]

    assert total("date_from=2026-11-03&date_to=2026-11-03") == 1
    assert total("date_to=2026-11-02") == 0
    assert total("date_from=2026-11-04") == 0
