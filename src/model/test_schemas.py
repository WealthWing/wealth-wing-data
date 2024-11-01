from pydantic import BaseModel, Field

class TestTableBase(BaseModel):
    name: str = Field(..., description="The name of the test entry")

class TestTableCreate(TestTableBase):
    pass

class TestTableResponse(TestTableBase):
    id: int = Field(..., description="The ID of the test entry")

    class Config:
        from_attributes = True