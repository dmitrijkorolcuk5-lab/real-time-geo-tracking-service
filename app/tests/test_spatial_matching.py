from __future__ import annotations

from app.repositories.geozone_repository import GeozoneRepository


def test_matching_statement_uses_postgis_distance() -> None:
    repository = GeozoneRepository()
    statement = repository.build_matching_statement(
        user_id="user-123",
        latitude=49.8397,
        longitude=24.0297,
    )

    compiled = str(statement.compile())

    assert "ST_DWithin" in compiled
    assert "geography" in compiled
    assert "geozones.radius_m" in compiled
    assert "ST_GeogFromText" in compiled or "ST_MakePoint" in compiled