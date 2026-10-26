import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, func, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from services.auth import AuthenticatedUser, get_current_user, require_role


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://program:test@localhost:5432/statistics")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
STATS_TOPIC = os.getenv("STATS_TOPIC", "car-rental-events")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Event(Base):
    __tablename__ = "stats_events"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    username = Column(String(80), nullable=False, index=True)
    method = Column(String(16), nullable=True)
    url = Column(String(255), nullable=True)
    status = Column(Integer, nullable=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class SummaryResponse(BaseModel):
    totalEvents: int
    actions: Dict[str, int]
    users: Dict[str, int]


class EventResponse(BaseModel):
    id: int
    action: str
    username: str
    method: Optional[str] = None
    url: Optional[str] = None
    status: Optional[int] = None
    payload: dict
    createdAt: str


app = FastAPI(title="Statistics Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed_ms = int((time.time() - start) * 1000)
    print(f"statistics-service {request.method} {request.url.path} -> {response.status_code} ({elapsed_ms} ms)")
    return response


def get_db():
    ensure_schema()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    existing = {column["name"] for column in inspect(engine).get_columns("stats_events")}
    migrations = [
        ("method", "ALTER TABLE stats_events ADD COLUMN method VARCHAR(16)"),
        ("url", "ALTER TABLE stats_events ADD COLUMN url VARCHAR(255)"),
        ("status", "ALTER TABLE stats_events ADD COLUMN status INTEGER"),
    ]
    with engine.begin() as connection:
        for column, statement in migrations:
            if column not in existing:
                connection.execute(text(statement))


def save_event(event: dict) -> None:
    db = SessionLocal()
    try:
        ensure_schema()
        db.add(
            Event(
                action=str(event.get("action", "unknown")),
                username=str(event.get("user", "unknown")),
                method=event.get("method"),
                url=event.get("url"),
                status=event.get("status"),
                payload=json.dumps(event.get("payload", {})),
                created_at=datetime.fromtimestamp(int(event.get("timestamp", time.time()))),
            )
        )
        db.commit()
    except Exception as exc:
        print(f"Failed to save statistics event: {exc}")
        db.rollback()
    finally:
        db.close()


def consume_events() -> None:
    if not KAFKA_BOOTSTRAP_SERVERS:
        print("Statistics consumer disabled: KAFKA_BOOTSTRAP_SERVERS is empty")
        return
    while True:
        try:
            from kafka import KafkaConsumer

            consumer = KafkaConsumer(
                STATS_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                group_id="statistics-service",
                value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            )
            for message in consumer:
                save_event(message.value)
        except Exception as exc:
            print(f"Statistics consumer retry after error: {exc}")
            time.sleep(5)


@app.on_event("startup")
def startup() -> None:
    ensure_schema()
    threading.Thread(target=consume_events, daemon=True).start()


@app.get("/manage/health")
async def health_check():
    return {"status": "OK"}


@app.get("/api/v1/statistics/summary", response_model=SummaryResponse)
async def summary(user: AuthenticatedUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, "Admin")
    total = db.query(Event).count()
    action_rows = db.query(Event.action, func.count(Event.id)).group_by(Event.action).all()
    user_rows = db.query(Event.username, func.count(Event.id)).group_by(Event.username).all()
    return SummaryResponse(
        totalEvents=total,
        actions={name: count for name, count in action_rows},
        users={name: count for name, count in user_rows},
    )


@app.get("/api/v1/statistics/events", response_model=List[EventResponse])
async def events(user: AuthenticatedUser = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(user, "Admin")
    rows = db.query(Event).order_by(Event.id.desc()).limit(100).all()
    return [
        EventResponse(
            id=row.id,
            action=row.action,
            username=row.username,
            method=row.method,
            url=row.url,
            status=row.status,
            payload=json.loads(row.payload),
            createdAt=row.created_at.isoformat(),
        )
        for row in rows
    ]
