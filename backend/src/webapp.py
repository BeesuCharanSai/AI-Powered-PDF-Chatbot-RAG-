"""Custom auth routes, merged into the LangGraph API server.

LangGraph's dev server supports mounting a custom Starlette/FastAPI app
alongside its built-in routes (see `http.app` in langgraph.json). This file
defines a small, self-contained auth system (signup/login/session) backed by
a local SQLite database, so the frontend's login and sign-up pages can work
against real accounts without needing a separate server or a third-party
auth provider.

Endpoints:
    POST /auth/signup  {name, email, password} -> {token, user}
    POST /auth/login   {email, password}        -> {token, user}
    GET  /auth/me       (Authorization: Bearer <token>) -> {user}

Passwords are hashed with bcrypt; sessions are signed JWTs. This is meant
for local development / demo purposes -- for a real production deployment,
put this behind HTTPS and use a proper secret management setup.
"""

import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "auth.db")
JWT_SECRET = os.environ.get(
    "AUTH_SECRET_KEY", "dev-insecure-secret-change-me-before-deploying-anywhere-real"
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 60 * 60 * 24 * 7  # 7 days


app = FastAPI(title="Auth API")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()


init_db()


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def make_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": time.time() + JWT_EXPIRY_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc


def get_current_user_id(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    return decode_token(token)


def user_to_dict(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


@app.post("/auth/signup")
def signup(payload: SignupRequest):
    email = payload.email.lower()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409, detail="An account with this email already exists"
            )

        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(
            payload.password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, payload.name, email, password_hash, time.time()),
        )
        conn.commit()

    token = make_token(user_id)
    return {"token": token, "user": {"id": user_id, "name": payload.name, "email": email}}


@app.post("/auth/login")
def login(payload: LoginRequest):
    email = payload.email.lower()
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not row or not bcrypt.checkpw(
        payload.password.encode("utf-8"), row["password_hash"].encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = make_token(row["id"])
    return {"token": token, "user": user_to_dict(row)}


@app.get("/auth/me")
def me(user_id: str = Depends(get_current_user_id)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {"user": user_to_dict(row)}
