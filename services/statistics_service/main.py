import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, List

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, func
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


def get_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_event(event: dict) -> None:
    db = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        db.add(
            Event(
                action=str(event.get("action", "unknown")),
                username=str(event.get("user", "unknown")),
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
    Base.metadata.create_all(bind=engine)
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
            payload=json.loads(row.payload),
            createdAt=row.created_at.isoformat(),
        )
        for row in rows
    ]
