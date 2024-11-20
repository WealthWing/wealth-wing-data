from typing import List
from fastapi import APIRouter, HTTPException
from src.model.models import Category
from src.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from src.database.connect import db_session


category_router = APIRouter()

# TODO: missing response model
@category_router.post("/create", status_code=201)
async def create_category(category_data: CategoryCreate, db: db_session):

    new_category = Category(
        type=category_data.type,
        description=category_data.description,
        title=category_data.title,
    )
    try:
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create category: {e}")

    return new_category


@category_router.get("/categories")
async def get_categories(db: db_session):
 
 
    try:
        categories = db.query(Category).all()
  
        if not categories:
            raise HTTPException(status_code=404, detail="No categories found")
        
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {e}")




@category_router.put(
    "/update/{category_id}", status_code=201, response_model=CategoryResponse
)
async def update_category(
    category_data: CategoryUpdate,
    category_id: str,
    db: db_session,
):

    category_model = db.query(Category).filter(Category.uuid == category_id).first()

    if not category_model:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        category_dict = category_data.model_dump(exclude_unset=True)
        print(category_dict, "category_dict")
        for key, value in category_dict.items():
            if getattr(category_model, key) != value:
                setattr(category_model, key, value)

        db.add(category_model)
        db.commit()
        db.refresh(category_model)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update category: {e}")

    return category_model
