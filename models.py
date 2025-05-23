from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum
from 
    rating = Column(Integer, default=0)
    rating_count = Column(Integer, default=0)

    user = relationship("User", back_populates="client")
    appointments = relationship("Appointment", back_populates="client")

# М
    id = Column(Integer, primary_key=True, autoincrement=True)
    specialist_id = Column(Integer, ForeignKey("specialists.id"), nullable=False)
    report_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(tz=config.TIMEZONE))
    specialist = relationship("Specialist", back_populates="reports")
