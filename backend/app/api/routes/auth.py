"""Authentication API routes: registration, login, profile check, and logout."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.database import crud
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _to_user_response(user_dict: dict) -> UserResponse:
    """Format MongoDB user dict into UserResponse schema."""
    return UserResponse(
        id=user_dict["id"],
        email=user_dict["email"],
        name=user_dict.get("name", user_dict["email"].split("@")[0].capitalize()),
        avatar=user_dict.get("avatar"),
        tier=user_dict.get("tier", "free"),
        created_at=user_dict.get("created_at"),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest):
    """Register a new user account with email and password."""
    existing = await crud.get_user_by_email(req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    display_name = req.name or req.full_name or req.email.split("@")[0].capitalize()
    password_hash = get_password_hash(req.password)
    user = await crud.create_user(
        email=req.email,
        password_hash=password_hash,
        name=display_name,
    )
    logger.info(f"User registered successfully: {req.email} (ID: {user['id']})")

    token = create_access_token(data={"sub": user["id"], "email": user["email"]})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=_to_user_response(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest):
    """Authenticate user with email and password, returning JWT session token."""
    user = await crud.get_user_by_email(req.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    await crud.update_user_last_login(user["id"])
    logger.info(f"User logged in: {req.email}")

    token = create_access_token(data={"sub": user["id"], "email": user["email"]})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=_to_user_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return profile details for the currently authenticated user session."""
    return _to_user_response(current_user)


@router.post("/logout")
async def logout():
    """Client-side logout acknowledgement."""
    return {"message": "Successfully logged out"}
