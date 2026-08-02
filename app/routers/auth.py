from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import users_collection
from app.models.user import UserCreate, UserInDB, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


def user_doc_to_out(user: dict) -> UserOut:
    """Convert a raw MongoDB document into the safe response schema (no password_hash)."""
    return UserOut(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        role=user["role"],
        phone=user["phone"],
        address=user["address"],
        is_verified=user["is_verified"],
        created_at=user["created_at"],
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    # 1. Check email isn't already taken
    existing = await users_collection.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Hash the password — never store plain text
    hashed = hash_password(user_in.password)

    # 3. Build the DB document
    user_data = UserInDB(
        name=user_in.name,
        email=user_in.email,
        password_hash=hashed,
        role=user_in.role,
        phone=user_in.phone,
        address=user_in.address,
        # Donors/Admins are auto-verified; NGOs start pending until an admin verifies them
        is_verified=(user_in.role != "ngo"),
    )

    result = await users_collection.insert_one(user_data.model_dump())
    created_user = await users_collection.find_one({"_id": result.inserted_id})

    return user_doc_to_out(created_user)


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Uses OAuth2PasswordRequestForm so this works directly with the /docs 'Authorize' button.
    form_data.username is actually the email (OAuth2 spec calls the field 'username').
    """
    user = await users_collection.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": str(user["_id"]), "role": user["role"]})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_doc_to_out(user),
    }


@router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    return user_doc_to_out(current_user)