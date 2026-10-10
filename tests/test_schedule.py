from datetime import date, timedelta

import pytest

from blogboard.run import WEEKLY_SCHEDULE, scheduled_domain


@pytest.mark.parametrize(
    ("day", "domain"),
    list(zip(range(7), WEEKLY_SCHEDULE, strict=True)),
)
def test_scheduled_domain_matches_weekday(day: int, domain: str) -> None:
    monday = date(2026, 10, 5)

    assert scheduled_domain((monday + timedelta(days=day)).isoformat()) == domain


def test_scheduled_domain_rejects_invalid_date() -> None:
    with pytest.raises(ValueError):
        scheduled_domain("not-a-date")
