from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import hmac
import hashlib
import json
from datetime import datetime, timedelta
import models, schemas, database

app = FastAPI()

SECRET_KEY = "your_secret_key"

ACCESS_TOKEN_EXPIRE_MINUTES = 30

models.Base.metadata.create_all(bind=database.engine)

def encode_base64(data: dict) -> str:
    json_data = json.dumps(data, separators=(",", ":"))
    return base64.urlsafe_b64encode(json_data.encode()).decode().strip("=")

def decode_base64(encoded_data: str) -> dict:
    padding = "=" * (4 - len(encoded_data) % 4)
    data = base64.urlsafe_b64decode(encoded_data + padding).decode()
    return json.loads(data)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire.isoformat()})
    
    encoded_header = encode_base64({"alg": "HS256", "typ": "JWT"})
    encoded_payload = encode_base64(to_encode)
    
    message = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()

    return f"{encoded_header}.{encoded_payload}.{signature}"

def decode_access_token(token: str) -> dict:
    try:
        header_b64, payload_b64, signature = token.split(".")
        message = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()

        if signature != expected_signature:
            raise HTTPException(status_code=401, detail="Invalid token signature")

        payload = decode_base64(payload_b64)
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")

    token = authorization[7:]  # Извлекаем токен после "Bearer "
    payload = decode_access_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.login == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.login == user.login).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Login already registred")
    new_user = models.User(
        first_name=None,
        last_name=None,
        birth_date=None,
        email=user.email,
        phone_number=None,
        login=user.login,
        hashed_password=generate_password_hash(user.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token")
def login_for_access_token(login_data: schemas.LoginSchema, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.login == login_data.login).first()
    if not user or not check_password_hash(user.hashed_password, login_data.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.login})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(get_current_user)):
    return current_user

@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return db_user


@app.put("/users/me/first_name")
def update_first_name(user_update: schemas.UserUpdate, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.first_name = user_update.first_name
    db.commit()
    db.refresh(current_user)
    return {"message": "First name updated successfully"}

@app.put("/users/me/last_name")
def update_last_name(user_update: schemas.UserUpdate, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.last_name = user_update.last_name
    db.commit()
    db.refresh(current_user)
    return {"message": "Last name updated successfully"}

@app.put("/users/me/birth_date")
def update_birth_date(user_update: schemas.UserUpdate, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.birth_date = user_update.birth_date
    db.commit()
    db.refresh(current_user)
    return {"message": "Birth date updated successfully"}

@app.put("/users/me/email")
def update_email(user_update: schemas.UserUpdate, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.email = user_update.email
    db.commit()
    db.refresh(current_user)
    return {"message": "Email updated successfully"}

@app.put("/users/me/phone_number")
def update_phone_number(user_update: schemas.UserUpdate, current_user: schemas.User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.phone_number = user_update.phone_number
    db.commit()
    db.refresh(current_user)
    return {"message": "Phone number updated successfully"}
