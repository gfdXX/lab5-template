import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

import jwt
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from services.auth import AuthenticatedUser, get_current_user, require_role


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://program:test@localhost:5432/identity")
ISSUER = os.getenv("OIDC_ISSUER", "http://localhost:8090")
AUDIENCE = os.getenv("OIDC_AUDIENCE", "car-rental-ui")
CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "car-rental-ui")
CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "car-rental-ui-secret")
DEFAULT_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://localhost:3000/callback")
TOKEN_TTL_SECONDS = int(os.getenv("OIDC_TOKEN_TTL_SECONDS", "3600"))
SIGNING_SECRET = os.getenv("OIDC_SIGNING_SECRET", "rsoi-coursework-signing-secret")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
DEMO_USERNAME = os.getenv("DEMO_USERNAME")
DEMO_EMAIL = os.getenv("DEMO_EMAIL")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "identity_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), nullable=False, default="User")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AuthorizationCode(Base):
    __tablename__ = "identity_authorization_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(80), unique=True, nullable=False, index=True)
    username = Column(String(80), nullable=False, index=True)
    client_id = Column(String(120), nullable=False)
    redirect_uri = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)


class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    fullName: Optional[str] = None


class UserResponse(BaseModel):
    username: str
    email: str
    fullName: str
    role: str


app = FastAPI(title="Identity Provider", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_admin_user(db)
        yield db
    finally:
        db.close()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def password_hash(password: str) -> str:
    salt = os.getenv("PASSWORD_SALT", "rsoi-coursework")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return _b64url(digest)


def verify_password(password: str, expected_hash: str) -> bool:
    return hmac.compare_digest(password_hash(password), expected_hash)


def jwk() -> dict:
    return {
        "kty": "oct",
        "kid": "identity-hs256",
        "alg": "HS256",
        "use": "sig",
        "k": _b64url(SIGNING_SECRET.encode()),
    }


def ensure_admin_user(db: Session) -> None:
    admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if not admin:
        db.add(
            User(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL,
                full_name="Administrator",
                password_hash=password_hash(ADMIN_PASSWORD),
                role="Admin",
            )
        )
        db.commit()

    if DEMO_USERNAME and DEMO_EMAIL and DEMO_PASSWORD:
        demo = db.query(User).filter(User.username == DEMO_USERNAME).first()
        if not demo:
            db.add(
                User(
                    username=DEMO_USERNAME,
                    email=DEMO_EMAIL,
                    full_name=DEMO_USERNAME,
                    password_hash=password_hash(DEMO_PASSWORD),
                    role="User",
                )
            )
            db.commit()


def normalize_scope(scope: Optional[str]) -> str:
    requested = set((scope or "openid profile email").split())
    requested.add("openid")
    return " ".join(item for item in ["openid", "profile", "email"] if item in requested)


def token_for(user: User, scope: str) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": user.username,
        "preferred_username": user.username,
        "roles": [user.role],
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
        "scope": scope,
    }
    parts = set(scope.split())
    if "profile" in parts:
        claims["name"] = user.full_name
    if "email" in parts:
        claims["email"] = user.email
    return jwt.encode(claims, SIGNING_SECRET, algorithm="HS256", headers={"kid": "identity-hs256"})


def login_page(message: str = "", **values) -> str:
    params = {
        "client_id": values.get("client_id", CLIENT_ID),
        "redirect_uri": values.get("redirect_uri", DEFAULT_REDIRECT_URI),
        "response_type": values.get("response_type", "code"),
        "scope": values.get("scope", "openid profile email"),
        "state": values.get("state", ""),
    }
    hidden = "\n".join(f'<input type="hidden" name="{key}" value="{value}">' for key, value in params.items())
    error = f'<div class="error">{message}</div>' if message else ""
    return f"""
    <!doctype html>
    <html>
    <head>
      <title>Car Rental Identity</title>
      <style>
        body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: Arial, sans-serif; background: #f5f7fb; color: #172033; }}
        form {{ width: 360px; background: white; border: 1px solid #d8deea; padding: 28px; border-radius: 8px; box-shadow: 0 16px 40px rgba(20, 28, 45, .08); }}
        h1 {{ margin: 0 0 20px; font-size: 22px; }}
        label {{ display: block; margin: 14px 0 6px; font-size: 13px; font-weight: 700; }}
        input {{ width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid #b9c3d5; border-radius: 6px; }}
        button {{ width: 100%; margin-top: 20px; padding: 11px; border: 0; border-radius: 6px; background: #2364d2; color: white; font-weight: 700; cursor: pointer; }}
        .error {{ margin-bottom: 12px; color: #9f1d20; font-size: 14px; }}
      </style>
    </head>
    <body>
      <form method="post" action="/oauth/authorize">
        <h1>Sign in</h1>
        {error}
        {hidden}
        <label>Username</label>
        <input name="username" autocomplete="username" required>
        <label>Password</label>
        <input name="password" type="password" autocomplete="current-password" required>
        <button type="submit">Continue</button>
      </form>
    </body>
    </html>
    """


@app.get("/manage/health")
async def health_check():
    return {"status": "OK"}


@app.get("/.well-known/openid-configuration")
async def well_known():
    return {
        "issuer": ISSUER,
        "authorization_endpoint": f"{ISSUER}/oauth/authorize",
        "token_endpoint": f"{ISSUER}/oauth/token",
        "jwks_uri": f"{ISSUER}/oauth/jwks",
        "response_types_supported": ["code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["HS256"],
        "scopes_supported": ["openid", "profile", "email"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        "claims_supported": ["sub", "preferred_username", "name", "email", "roles"],
    }


@app.get("/oauth/jwks")
async def jwks():
    return {"keys": [jwk()]}


@app.get("/oauth/authorize", response_class=HTMLResponse)
async def authorize_form(
    client_id: str = Query(...),
    redirect_uri: str = Query(DEFAULT_REDIRECT_URI),
    response_type: str = Query("code"),
    scope: str = Query("openid profile email"),
    state: str = Query(""),
):
    if client_id != CLIENT_ID or response_type != "code":
        raise HTTPException(status_code=400, detail="Invalid authorization request")
    return HTMLResponse(login_page(client_id=client_id, redirect_uri=redirect_uri, response_type=response_type, scope=scope, state=state))


@app.post("/oauth/authorize")
async def authorize_submit(
    client_id: str = Form(...),
    redirect_uri: str = Form(DEFAULT_REDIRECT_URI),
    response_type: str = Form("code"),
    scope: str = Form("openid profile email"),
    state: str = Form(""),
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if client_id != CLIENT_ID or response_type != "code":
        raise HTTPException(status_code=400, detail="Invalid authorization request")
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return HTMLResponse(
            login_page("Invalid username or password", client_id=client_id, redirect_uri=redirect_uri, response_type=response_type, scope=scope, state=state),
            status_code=401,
        )
    code = _b64url(uuid.uuid4().bytes + uuid.uuid4().bytes)
    db.add(
        AuthorizationCode(
            code=code,
            username=user.username,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=normalize_scope(scope),
            expires_at=datetime.utcnow() + timedelta(minutes=5),
        )
    )
    db.commit()
    params = {"code": code}
    if state:
        params["state"] = state
    return RedirectResponse(f"{redirect_uri}?{urlencode(params)}", status_code=303)


@app.post("/oauth/token")
async def token(
    response: Response,
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    redirect_uri: str = Form(DEFAULT_REDIRECT_URI),
    scope: str = Form("openid profile email"),
    db: Session = Depends(get_db),
):
    if client_id != CLIENT_ID or client_secret != CLIENT_SECRET:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    if grant_type == "authorization_code":
        auth_code = db.query(AuthorizationCode).filter(AuthorizationCode.code == code).first()
        if not auth_code or auth_code.used_at or auth_code.expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invalid authorization code")
        if auth_code.client_id != client_id or auth_code.redirect_uri != redirect_uri:
            raise HTTPException(status_code=400, detail="Authorization code was issued for another client")
        user = db.query(User).filter(User.username == auth_code.username).first()
        auth_code.used_at = datetime.utcnow()
        db.commit()
        final_scope = auth_code.scope
    elif grant_type in ("password", "http://auth0.com/oauth/grant-type/password-realm"):
        user = db.query(User).filter(User.username == username).first()
        if not user or not password or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        final_scope = normalize_scope(scope)
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant type")

    access_token = token_for(user, final_scope)
    response.headers["Cache-Control"] = "no-store"
    return {
        "access_token": access_token,
        "id_token": access_token,
        "token_type": "Bearer",
        "expires_in": TOKEN_TTL_SECONDS,
        "scope": final_scope,
    }


@app.get("/api/v1/users", response_model=list[UserResponse])
async def list_users(user: AuthenticatedUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, "Admin")
    return [
        UserResponse(username=item.username, email=item.email, fullName=item.full_name, role=item.role)
        for item in db.query(User).order_by(User.id).all()
    ]


@app.post("/api/v1/users", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_role(user, "Admin")
    exists = db.query(User).filter((User.username == payload.username) | (User.email == payload.email)).first()
    if exists:
        raise HTTPException(status_code=409, detail="User already exists")
    new_user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.fullName or payload.username,
        password_hash=password_hash(payload.password),
        role="User",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse(username=new_user.username, email=new_user.email, fullName=new_user.full_name, role=new_user.role)


@app.get("/api/v1/me", response_model=UserResponse)
async def me(user: AuthenticatedUser = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(User).filter(User.username == user.username).first()
    if not item:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(username=item.username, email=item.email, fullName=item.full_name, role=item.role)
