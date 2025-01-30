from sqlalchemy.ext.asyncio import AsyncSession

from crud.vehicle import VehicleOperation
from crud.user import UserOperation
from crud.gate import GateOperation


class VehicleAccessChecker:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def is_vehicle_allowed(self, plate_number: str, gate_id: int):
        """
        Checks if a vehicle is allowed to pass through a specific gate.

        :param plate_number: License plate number of the vehicle.
        :param gate_id: ID of the gate where the check is performed.
        :return: Tuple (is_accessible: bool, db_vehicle: DBVehicle, db_owner: DBUser)
        """
        # Step 1: Find Vehicle by Plate Number
        db_vehicle = await VehicleOperation(self.db_session).get_one_vehcile_plate(plate_number)
        if not db_vehicle:
            print(f"[WARNING] Vehicle with plate number {plate_number} not found.")
            return False, None, None

        # Step 2: Find Owner of the Vehicle
        db_owner = await UserOperation(self.db_session).get_one_object_id(db_vehicle.owner_id)
        if not db_owner:
            print(f"[WARNING] Owner for vehicle {plate_number} not found.")
            return False, db_vehicle, None

        # Step 3: Check If Owner Has Access to the Gate
        accessible_gate_ids = {gate.id for gate in db_owner.accessible_gates}
        is_accessible = gate_id in accessible_gate_ids

        print(f"[INFO] Vehicle {plate_number} access at gate {gate_id}: {'ALLOWED' if is_accessible else 'DENIED'}")

        return is_accessible, db_vehicle, db_owner
