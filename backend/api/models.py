from typing import Any
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base: Any = declarative_base()


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(80), nullable=False)
    status = Column(String(20), nullable=False)
    target = Column(String(50), nullable=False)
    config = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=True)
    n_features = Column(Integer, nullable=True)
    n_train = Column(Integer, nullable=True)
    n_val = Column(Integer, nullable=True)
    n_test = Column(Integer, nullable=True)
    best_epoch = Column(Integer, nullable=True)
    duration_s = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(String, nullable=True)

    epochs = relationship("RunEpoch", back_populates="run", cascade="all, delete-orphan")


class RunEpoch(Base):
    __tablename__ = "run_epochs"

    id = Column(Integer, primary_key=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    epoch = Column(Integer, nullable=False)
    loss_train = Column(Float, nullable=False)
    loss_val = Column(Float, nullable=False)
    acc_train = Column(Float, nullable=False)
    acc_val = Column(Float, nullable=False)
    f1_val = Column(Float, nullable=False)
    lr = Column(Float, nullable=False)
    grad_norm = Column(Float, nullable=False)
    seconds = Column(Float, nullable=False)

    run = relationship("Run", back_populates="epochs")
