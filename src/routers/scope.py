from fastapi import APIRouter, Depends, HTTPException


scope_router = APIRouter()

@scope_router.put("/create", status_code=201)
async def create_scope():
    return {"message": "Project created successfully!"}