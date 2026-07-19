"""Unit tests for delivery request models.

Covers task 4.1 of shipping-courier-integration: model-level validation for
`DeliveryOffice`, `DeliveryDoor`, `DeliveryInfo`, and phone normalization.
"""

import pytest
from pydantic import ValidationError

from app.models.delivery import DeliveryDoor, DeliveryInfo, DeliveryOffice


class TestDeliveryOffice:
    """Field-level validation for the office-pickup sub-object."""

    def test_valid_office_payload(self):
        office = DeliveryOffice(
            courier="speedy",
            office_id="speedy-sf-001",
            office_name="София Център - бул. Витоша 50",
            office_type="office",
            phone="+359888123456",
        )
        assert office.courier == "speedy"
        assert office.office_type == "office"

    def test_locker_type(self):
        office = DeliveryOffice(
            courier="econt",
            office_id="econt-2",
            office_name="Автомат София",
            office_type="apt",
            phone="+359888999888",
        )
        assert office.office_type == "apt"

    @pytest.mark.parametrize(
        "raw,normalized",
        [
            ("+359 888 123 456", "+359888123456"),
            ("+359-888-123-456", "+359888123456"),
            ("(0888) 123 456", "0888123456"),
            ("0888123456", "0888123456"),
        ],
    )
    def test_phone_normalization(self, raw, normalized):
        office = DeliveryOffice(
            courier="speedy",
            office_id="x",
            office_name="Test",
            office_type="office",
            phone=raw,
        )
        assert office.phone == normalized

    @pytest.mark.parametrize(
        "bad_phone",
        [
            "12345",  # too short (5 digits < 8)
            "abcdefgh",  # no digits
            "+" + "1" * 16,  # too long (16 digits > 15)
            "",
        ],
    )
    def test_invalid_phone_rejected(self, bad_phone):
        with pytest.raises(ValidationError):
            DeliveryOffice(
                courier="speedy",
                office_id="x",
                office_name="Test",
                office_type="office",
                phone=bad_phone,
            )

    def test_invalid_courier_rejected(self):
        with pytest.raises(ValidationError):
            DeliveryOffice(
                courier="dhl",  # type: ignore[arg-type]
                office_id="x",
                office_name="Test",
                office_type="office",
                phone="+359888123456",
            )

    def test_invalid_office_type_rejected(self):
        with pytest.raises(ValidationError):
            DeliveryOffice(
                courier="speedy",
                office_id="x",
                office_name="Test",
                office_type="warehouse",  # type: ignore[arg-type]
                phone="+359888123456",
            )

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValidationError):
            DeliveryOffice(
                courier="speedy",
                office_id="x",
                office_name="Test",
                office_type="office",
                # phone missing
            )  # type: ignore[call-arg]


class TestDeliveryDoor:
    """Field-level validation for the door-delivery sub-object."""

    def test_valid_full_address(self):
        door = DeliveryDoor(
            courier="econt",
            city="София",
            postal_code="1000",
            street="бул. Витоша 100",
            building="Б",
            apartment="12",
            phone="+359888123456",
        )
        assert door.city == "София"
        assert door.building == "Б"

    def test_optional_building_and_apartment(self):
        door = DeliveryDoor(
            courier="speedy",
            city="Пловдив",
            postal_code="4000",
            street="ул. Главна 5",
            phone="+359888111222",
        )
        assert door.building is None
        assert door.apartment is None

    def test_invalid_phone_rejected(self):
        with pytest.raises(ValidationError):
            DeliveryDoor(
                courier="econt",
                city="София",
                postal_code="1000",
                street="ул. Витоша 1",
                phone="123",
            )

    def test_missing_required_fields_rejected(self):
        # Missing street
        with pytest.raises(ValidationError):
            DeliveryDoor(
                courier="econt",
                city="София",
                postal_code="1000",
                phone="+359888123456",
            )  # type: ignore[call-arg]

    def test_empty_string_field_rejected(self):
        # min_length=1 on required text fields
        with pytest.raises(ValidationError):
            DeliveryDoor(
                courier="econt",
                city="",  # empty
                postal_code="1000",
                street="ул. Витоша 1",
                phone="+359888123456",
            )


class TestDeliveryInfo:
    """Top-level `method` gating and mutual exclusion of office/door."""

    def _office(self) -> dict:
        return {
            "courier": "econt",
            "office_id": "1",
            "office_name": "Sofia",
            "office_type": "office",
            "phone": "+359888123456",
        }

    def _door(self) -> dict:
        return {
            "courier": "econt",
            "city": "София",
            "postal_code": "1000",
            "street": "ул. Витоша 1",
            "phone": "+359888123456",
        }

    def test_office_method_with_office_details(self):
        info = DeliveryInfo(method="office", office=self._office())  # type: ignore[arg-type]
        assert info.method == "office"
        assert info.office is not None
        assert info.door is None

    def test_door_method_with_door_details(self):
        info = DeliveryInfo(method="door", door=self._door())  # type: ignore[arg-type]
        assert info.method == "door"
        assert info.door is not None
        assert info.office is None

    def test_office_method_missing_office_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DeliveryInfo(method="office")
        assert "office details required" in str(exc_info.value)

    def test_door_method_missing_door_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DeliveryInfo(method="door")
        assert "door details required" in str(exc_info.value)

    def test_office_method_with_door_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DeliveryInfo(
                method="office",
                office=self._office(),  # type: ignore[arg-type]
                door=self._door(),  # type: ignore[arg-type]
            )
        assert "door details must be null" in str(exc_info.value)

    def test_door_method_with_office_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DeliveryInfo(
                method="door",
                door=self._door(),  # type: ignore[arg-type]
                office=self._office(),  # type: ignore[arg-type]
            )
        assert "office details must be null" in str(exc_info.value)

    def test_invalid_method_rejected(self):
        with pytest.raises(ValidationError):
            DeliveryInfo(method="pigeon")  # type: ignore[arg-type]
