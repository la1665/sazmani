from jose import jwt, JWTError
from models.user import DBUser
from crud.user import UserOperation
from settings import settings

async def get_user_from_token(token: str, db):
    try:
        if settings.SECRET_KEY and settings.ALGORITHM:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            personal_number = payload.get("sub")
            if not personal_number:
                return None

            user_op = UserOperation(db)
            return await user_op.get_user_personal_number(personal_number)
    except JWTError as exp:
        print("jwt error", exp)
        return None
