from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.authorization import get_current_active_user, get_admin_user, get_admin_or_staff_user
from database.engine import get_db
from schema.user import UserInDB
from schema.camera import CameraPagination
from schema.gate import GateCreate, GateUpdate, GateInDB, GatePagination
from crud.gate import GateOperation
from utils.middlewwares import check_password_changed


gate_router = APIRouter(
    prefix="/v1/gates",
    tags=["gates"],
)


@gate_router.post("/", response_model=GateInDB, status_code=status.HTTP_201_CREATED, dependencies=[Depends(check_password_changed)])
async def api_create_gate(gate: GateCreate, db: AsyncSession = Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    gate_op = GateOperation(db)
    return await gate_op.create_gate(gate)

@gate_router.get("/", response_model=GatePagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_all_gates(page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    gate_op = GateOperation(db)
    return await gate_op.get_all_objects(page, page_size)


@gate_router.get("/{gate_id}", response_model=GateInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_gate(gate_id: int, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    gate_op = GateOperation(db)
    return await gate_op.get_one_object_id(gate_id)


@gate_router.get("/{gate_id}/cameras", response_model=CameraPagination, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_get_gate_all_cameras(gate_id: int, page: int = 1, page_size: int = 10, db: AsyncSession = Depends(get_db), current_user: UserInDB = Depends(get_admin_or_staff_user)):
    gate_op = GateOperation(db)
    return await gate_op.get_gate_all_cameras(gate_id, page, page_size)


@gate_router.put("/{gate_id}", response_model=GateInDB, status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_update_gate(gate_id: int, gate: GateUpdate, db:AsyncSession=Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    gate_op = GateOperation(db)
    return await gate_op.update_gate(gate_id, gate)


@gate_router.delete("/{gate_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_delete_gate(gate_id: int, db:AsyncSession=Depends(get_db), current_user: UserInDB=Depends(get_admin_or_staff_user)):
    gate_op = GateOperation(db)
    return await gate_op.delete_object(gate_id)

@gate_router.patch("/{gate_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(check_password_changed)])
async def api_change_activation(
    gate_id: int,
    db: AsyncSession=Depends(get_db),
    current_user: UserInDB=Depends(get_admin_or_staff_user)
):
    gate_op = GateOperation(db)
    return await gate_op.change_activation_status(gate_id)
