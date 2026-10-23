from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..contracts.loader import blast_radius

router = APIRouter(tags=["contracts"])


@router.get("/contracts")
async def list_contracts(request: Request):
    store = request.app.state.services.contracts
    return [{"role": r, "latest_version": store.latest_version(r)} for r in store.roles()]


@router.get("/contracts/{role}")
async def get_contract(role: str, request: Request, version: int | None = None):
    c = request.app.state.services.contracts.get(role, version)
    if c is None:
        raise HTTPException(status_code=404, detail="contract not found")
    return c.to_dict()


@router.get("/contracts/{role}/blast-radius")
async def get_blast_radius(role: str, request: Request):
    svc = request.app.state.services
    c = svc.contracts.get(role)
    if c is None:
        raise HTTPException(status_code=404, detail="contract not found")
    return blast_radius(c, svc.registry)


@router.get("/tools")
async def list_tools(request: Request):
    return [{"name": s.name, "resource_class": s.resource_class, "sensitivity": s.sensitivity,
             "sink_type": s.sink_type, "manifest_hash": s.manifest_hash}
            for s in request.app.state.services.registry.all()]


@router.get("/decoys")
async def list_decoys(request: Request):
    """Decoy tripwires and how many times each has been touched."""
    return request.app.state.services.decoys.snapshot()
