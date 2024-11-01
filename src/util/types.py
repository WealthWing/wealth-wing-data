from pydantic import BaseModel

class UserPool(BaseModel):
    sub: str
    email: str