from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum
from config import config

Base = declarative_base()

# Перечисления для ролей и статусов
class Role(enum.Enum):
    CLIENT = "client"
    SPECIALIST = "specialist"
    ADMIN = "admin"

class AppointmentStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    CANCELED = "canceled"

# Модель пользователя
class User(Base):
    __tablename__ = "users"

    telegram_id = Column(String, primary_key=True)
    role = Column(Enum(Role), nullable=False)

    client = relationship("Client", uselist=False, back_populates="user")
    specialist = relationship("Specialist", uselist=False, back_populates="user")

# Модель клиента
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.telegram_id"), nullable=False)
    full_name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    rating = Column(Integer, default=0)
    rating_count = Column(Integer, default=0)

    user = relationship("User", back_populates="client")
    appointments = relationship("Appointment", back_populates="client")

# Модель специалиста
class Specialist(Base):
    __tablename__ = "specialists"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.telegram_id"), nullable=False)
    full_name = Column(String, nullable=False)
    username = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    completed_appointments = Column(Integer, default=0)
    rank = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    user = relationship("User", back_populates="specialist")
    appointments = relationship("Appointment", back_populates="specialist")
    reports = relationship("SpecialistReport", back_populates="specialist")

# Модель заявки
class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    specialist_id = Column(Integer, ForeignKey("specialists.id"), nullable=True)
    proposed_date = Column(DateTime, nullable=False)
    scheduled_time = Column(DateTime, nullable=True)
    complex = Column(String, nullable=True)
    reason = Column(Text, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING)
    reject_reason = Column(Text, nullable=True)

    client = relationship("Client", back_populates="appointments")
    specialist = relationship("Specialist", back_populates="appointments")
    notifications = relationship("NotificationSent", back_populates="appointment")

# Модель чёрного списка
class Blacklist(Base):
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    blocked_until = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=config.TIMEZONE))

# Модель для отслеживания отправленных уведомлений
class NotificationSent(Base):
    __tablename__ = "notifications_sent"

    id = Column(Integer, primary_key=True, autoincrement=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    reminder_type = Column(String, nullable=False)  # '1h', '5m', 'ready'
    sent_at = Column(DateTime, nullable=False, default=lambda: datetime.now(tz=config.TIMEZONE))

    appointment = relationship("Appointment", back_populates="notifications")

# Модель отчета специалиста
class SpecialistReport(Base):
    __tablename__ = "specialist_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    specialist_id = Column(Integer, ForeignKey("specialists.id"), nullable=False)
    report_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(tz=config.TIMEZONE))
    specialist = relationship("Specialist", back_populates="reports")