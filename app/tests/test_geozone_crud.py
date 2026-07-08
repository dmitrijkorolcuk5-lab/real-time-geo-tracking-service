import pytest

from app.schemas.geozone import GeozoneCreate, GeozoneUpdate


def test_geozone_create_validation() -> None:
    payload = GeozoneCreate(name="Zone", latitude=49.0, longitude=24.0, radius_m=100)
    assert payload.radius_m == 100


def test_geozone_update_validation() -> None:
    payload = GeozoneUpdate(name="Updated", radius_m=250)
    assert payload.name == "Updated"

