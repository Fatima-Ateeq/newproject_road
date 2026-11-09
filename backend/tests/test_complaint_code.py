from app.core.complaint_code import format_complaint_code, parse_complaint_code


def test_format_pads_the_id_to_six_digits():
    assert format_complaint_code(2026, 42) == "RW-2026-000042"


def test_parse_returns_year_and_id():
    assert parse_complaint_code("RW-2026-000042") == (2026, 42)


def test_parse_rejects_malformed_codes():
    for bad in ["", "rw-2026-000042", "RW-26-000042", "RW-2026-42", "RW-2026-000042x"]:
        assert parse_complaint_code(bad) is None
