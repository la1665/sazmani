from fastapi import Depends, HTTPException, status

from schema.user import UserInDB
from auth.authorization import get_current_active_user

async def check_password_changed(current_user: UserInDB = Depends(get_current_active_user)):
    """
    Restrict access to users who have not changed their password after the first login.
    """
    if not current_user.password_changed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must change your password before accessing this resource.",
        )
