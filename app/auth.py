from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import db_models
from .auth_models import TokenResponse, UserPublic, UserRegister
from .database import get_db
from .security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


router = APIRouter(tags=["authentication"])


@router.post(
    "/auth/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: UserRegister,
    db: Session = Depends(get_db),
):
    # Normalize emails so that Example@Email.com and example@email.com
    # are treated as the same address.
    normalized_email = str(data.email).strip().lower()

    existing_user = (
        db.query(db_models.User)
        .filter(db_models.User.email == normalized_email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = db_models.User(
        email=normalized_email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        # The unique constraint also protects against simultaneous requests.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    db.refresh(user)
    return user


@router.post(
    "/auth/login",
    response_model=TokenResponse,
)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    # OAuth2PasswordRequestForm calls this field "username".
    # For this project, enter the user's email in that field.
    normalized_email = form_data.username.strip().lower()

    user = (
        db.query(db_models.User)
        .filter(db_models.User.email == normalized_email)
        .first()
    )

    if user is None or not verify_password(
        form_data.password,
        user.hashed_password if user else hash_password(
            "constant-dummy-password-used-for-timing"
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get(
    "/users/me",
    response_model=UserPublic,
)
def read_current_user(
    current_user: Annotated[
        db_models.User,
        Depends(get_current_user),
    ],
):
    return current_user