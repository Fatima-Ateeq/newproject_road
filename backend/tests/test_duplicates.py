from app.ai.context import ComplaintContext
from app.ai.duplicates import NearbyDuplicateFinder
from app.core.enums import ComplaintStatus
from app.models import Complaint
from app.repositories.complaint_repository import ComplaintRepository


def add(db, text, lat, lon, status=ComplaintStatus.PENDING) -> Complaint:
    complaint = Complaint(description=text, latitude=lat, longitude=lon, status=status)
    db.add(complaint)
    db.commit()
    return complaint


def finder_for(db, **kwargs):
    return NearbyDuplicateFinder(ComplaintRepository(db), **kwargs)


def context_for(complaint: Complaint) -> ComplaintContext:
    return ComplaintContext(complaint.id, complaint.code, complaint.description,
                            complaint.latitude, complaint.longitude, False)


def test_finds_a_similar_complaint_close_by(session_factory):
    with session_factory() as db:
        this = add(db, "Deep pothole near the school gate", 31.5000, 74.3000)
        other = add(db, "Big pothole near the school gate on this road", 31.5003, 74.3000)
        matches = finder_for(db).find(context_for(this))
    assert [m.complaint_id for m in matches] == [other.code]
    assert 25 < matches[0].distance_m < 40


def test_ignores_complaints_that_are_too_far_or_about_something_else(session_factory):
    with session_factory() as db:
        this = add(db, "Deep pothole near the school gate", 31.5000, 74.3000)
        add(db, "Deep pothole near the school gate", 31.5100, 74.3000)       # about 1 km away
        add(db, "Street lights are off all night", 31.5001, 74.3000)          # close, different problem
        assert finder_for(db).find(context_for(this)) == []


def test_ignores_resolved_complaints_and_the_complaint_itself(session_factory):
    with session_factory() as db:
        this = add(db, "Deep pothole near the school gate", 31.5000, 74.3000)
        add(db, "Deep pothole near the school gate", 31.5001, 74.3000, ComplaintStatus.RESOLVED)
        assert finder_for(db).find(context_for(this)) == []


def test_best_matches_come_first_and_the_list_is_limited(session_factory):
    with session_factory() as db:
        this = add(db, "Deep pothole near the school gate", 31.5000, 74.3000)
        for i in range(4):
            add(db, "Deep pothole near the school gate", 31.5000 + i * 0.0001, 74.3000)
        matches = finder_for(db, limit=3).find(context_for(this))
    assert len(matches) == 3
    assert [m.distance_m for m in matches] == sorted(m.distance_m for m in matches)
