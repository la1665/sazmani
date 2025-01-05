from pydantic import BaseModel

from models.user import UserType

class Token(BaseModel):
    user_id: int
    user_type: UserType
    access_token: str
    token_type: str


class TokenData(BaseModel):
    personal_number: str
