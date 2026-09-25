from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from app.repositories.cargo_repository import cargo_repository
from app.repositories.port_repository import port_repository
from app.schemas.audit import AuditAction, AuditEntityType
from app.schemas.auth import UserProfileResponse
from app.schemas.cargo_request import CargoRequestCreate, CargoRequestResponse
from app.services.audit_service import audit_service


class CargoService:
    """Service handling domain logic and orchestration for Cargo Requests."""

    def create_cargo_request(
        self, data: CargoRequestCreate, user_profile: UserProfileResponse
    ) -> CargoRequestResponse:
        origin_port = data.origin_port_id.strip().upper()
        destination_port = data.destination_port_id.strip().upper()

        # 1. Validate origin port ID
        if not port_repository.is_valid_port(origin_port):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Origin port '{data.origin_port_id}' is invalid or not found in port catalog",
            )

        # 2. Validate destination port ID
        if not port_repository.is_valid_port(destination_port):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Destination port '{data.destination_port_id}' is invalid or not found in port catalog",
            )

        # 3. Construct persistent cargo request record linked to authenticated user_id
        cargo_request_id = uuid4()
        now_utc = datetime.now(timezone.utc).isoformat()

        record = {
            "cargo_request_id": str(cargo_request_id),
            "user_id": str(user_profile.user_id),
            "commodity": data.commodity.value,
            "cargo_volume_mt": float(data.cargo_volume_mt),
            "origin_port_id": origin_port,
            "destination_port_id": destination_port,
            "earliest_delivery_date": str(data.earliest_delivery_date),
            "latest_delivery_date": str(data.latest_delivery_date),
            "contract_horizon": data.contract_horizon.value,
            "created_at": now_utc,
        }

        # 4. Persist via repository
        saved = cargo_repository.create(record)

        # 5. Record audit event
        try:
            audit_service.record_event(
                user_id=user_profile.user_id,
                action=AuditAction.CREATE,
                entity_type=AuditEntityType.CARGO_REQUEST,
                entity_id=str(saved["cargo_request_id"]),
                details={
                    "commodity": saved["commodity"],
                    "cargo_volume_mt": saved["cargo_volume_mt"],
                    "origin_port_id": saved["origin_port_id"],
                    "destination_port_id": saved["destination_port_id"],
                    "contract_horizon": saved["contract_horizon"],
                },
            )
        except Exception:
            pass  # Audit logging failure must not fail primary cargo creation operation

        return CargoRequestResponse(
            cargo_request_id=UUID(str(saved["cargo_request_id"])),
            user_id=UUID(str(saved["user_id"])),
            commodity=saved["commodity"],
            cargo_volume_mt=float(saved["cargo_volume_mt"]),
            origin_port_id=saved["origin_port_id"],
            destination_port_id=saved["destination_port_id"],
            earliest_delivery_date=saved["earliest_delivery_date"],
            latest_delivery_date=saved["latest_delivery_date"],
            contract_horizon=saved["contract_horizon"],
            created_at=saved["created_at"],
        )

    def get_cargo_request(
        self, cargo_request_id: UUID, user_profile: UserProfileResponse
    ) -> CargoRequestResponse:
        record = cargo_repository.get_by_id(cargo_request_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cargo request not found",
            )

        record_user_id = str(record.get("user_id"))
        current_user_id = str(user_profile.user_id)
        is_owner = record_user_id == current_user_id
        is_elevated = user_profile.role in ["MANAGER", "ADMINISTRATOR"]

        if not is_owner and not is_elevated:
            # Hide inaccessible cargo requests with 404 to avoid leaking existence
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cargo request not found",
            )

        return CargoRequestResponse(
            cargo_request_id=UUID(str(record["cargo_request_id"])),
            user_id=UUID(str(record["user_id"])),
            commodity=record["commodity"],
            cargo_volume_mt=float(record["cargo_volume_mt"]),
            origin_port_id=record["origin_port_id"],
            destination_port_id=record["destination_port_id"],
            earliest_delivery_date=record["earliest_delivery_date"],
            latest_delivery_date=record["latest_delivery_date"],
            contract_horizon=record["contract_horizon"],
            created_at=record["created_at"],
        )

    def list_cargo_requests(
        self, user_profile: UserProfileResponse
    ) -> List[CargoRequestResponse]:
        records = cargo_repository.get_by_user_id(user_profile.user_id)
        results = []
        for r in records:
            results.append(
                CargoRequestResponse(
                    cargo_request_id=UUID(str(r["cargo_request_id"])),
                    user_id=UUID(str(r["user_id"])),
                    commodity=r["commodity"],
                    cargo_volume_mt=float(r["cargo_volume_mt"]),
                    origin_port_id=r["origin_port_id"],
                    destination_port_id=r["destination_port_id"],
                    earliest_delivery_date=r["earliest_delivery_date"],
                    latest_delivery_date=r["latest_delivery_date"],
                    contract_horizon=r["contract_horizon"],
                    created_at=r["created_at"],
                )
            )
        return results


cargo_service = CargoService()
