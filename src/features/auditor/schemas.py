from pydantic import BaseModel


class LoginSchema(BaseModel):
    success: bool
    message: str
