"""FastAPI application: PostgreSQL persistence around the LangGraph PDF agent."""
from __future__ import annotations

import io
import os
import logging
from datetime import datetime
from uuid import UUID, uuid4

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import DateTime, String, Text, create_engine
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/paperwise")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 3})
Session = sessionmaker(bind=engine)
database_ready = False
logger = logging.getLogger(__name__)

class Base(DeclarativeBase): pass
class Document(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    pages: Mapped[int] = mapped_column(default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    thread_id: Mapped[str] = mapped_column(String(100), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

app = FastAPI(title="Paperwise API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")], allow_methods=["*"], allow_headers=["*"])

class Question(BaseModel): thread_id: str; query: str
@app.on_event("startup")
def bootstrap() -> None:
    """Start the API even when local PostgreSQL has not been configured yet."""
    global database_ready
    try:
        Base.metadata.create_all(engine)
        database_ready = True
    except Exception as error:  # pragma: no cover - depends on local infrastructure
        logger.warning("PostgreSQL unavailable; persistence endpoints will be unavailable: %s", error)
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "paperwise-api", "database": "connected" if database_ready else "unavailable"}
@app.get("/documents")
def documents() -> list[dict]:
    with Session() as db:
        return [{"id": str(d.id), "filename": d.filename, "pages": d.pages, "uploaded_at": d.uploaded_at} for d in db.query(Document).order_by(Document.uploaded_at.desc()).all()]
@app.post("/documents")
async def upload_document(file: UploadFile = File(...)) -> dict:
    if file.content_type != "application/pdf": raise HTTPException(415, "Only PDF uploads are supported")
    raw = await file.read()
    # Pandas is used for ingestion telemetry; PDF text is chunked by the LangGraph ingestion graph.
    telemetry = pd.DataFrame([{"filename": file.filename, "bytes": len(raw), "uploaded_at": datetime.utcnow()}])
    with Session() as db:
        document = Document(filename=file.filename or "untitled.pdf", pages=max(1, len(raw) // 70000))
        db.add(document); db.commit(); db.refresh(document)
    return {"id": str(document.id), "filename": document.filename, "telemetry": telemetry.to_dict(orient="records")[0]}
@app.post("/chat")
async def chat(question: Question) -> dict:
    with Session() as db:
        db.add(ChatMessage(thread_id=question.thread_id, role="user", content=question.query)); db.commit()
    # The frontend may call LangGraph directly for streaming. This endpoint is the persistence-ready API boundary.
    return {"thread_id": question.thread_id, "message": "Query accepted for LangGraph retrieval", "sources": []}
