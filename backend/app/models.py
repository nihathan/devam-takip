import enum
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"       # Geldi
    ABSENT = "ABSENT"         # Gelmedi (Özürsüz)
    LATE = "LATE"             # Geç Kaldı
    EXCUSED = "EXCUSED"       # İzinli / Raporlu (Özürlü)

class RiskLevel(str, enum.Enum):
    LOW = "LOW"               # Düşük Risk (Yeşil)
    MEDIUM = "MEDIUM"         # Orta Risk (Sarı)
    HIGH = "HIGH"             # Yüksek Risk (Turuncu)
    CRITICAL = "CRITICAL"     # Kritik Risk (Kırmızı)

class ClassRoom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # örn: "10-A", "11-Fen-B"
    grade_level = Column(Integer, nullable=False)           # örn: 10, 11

    students = relationship("Student", back_populates="classroom", cascade="all, delete-orphan")
    sessions = relationship("LessonSession", back_populates="classroom")

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False) # örn: "Matematik", "Fizik"
    code = Column(String(20), nullable=True)                # örn: "MAT101"

    sessions = relationship("LessonSession", back_populates="subject")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String(20), unique=True, nullable=False, index=True) # örn: "1024"
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    class_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    
    parent_name = Column(String(100), nullable=False)
    parent_phone = Column(String(20), nullable=False)       # örn: "+905551234567"
    parent_email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    classroom = relationship("ClassRoom", back_populates="students")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    sms_logs = relationship("SMSAlertLog", back_populates="student", cascade="all, delete-orphan")
    intervention_notes = relationship("InterventionNote", back_populates="student", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

class LessonSession(Base):
    """
    Belirli bir sınıfın, belirli bir tarihteki ders saati oturumu.
    Örn: 10-A sınıfının 2026-10-04 tarihindeki 2. dersi (Fizik).
    """
    __tablename__ = "lesson_sessions"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    session_date = Column(Date, nullable=False, index=True)
    lesson_hour = Column(Integer, nullable=False)           # 1. ders, 2. ders vb.
    created_at = Column(DateTime, default=datetime.utcnow)

    classroom = relationship("ClassRoom", back_populates="sessions")
    subject = relationship("Subject", back_populates="sessions")
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")

class AttendanceRecord(Base):
    """
    Bir oturumdaki tek bir öğrencinin yoklama durumu.
    """
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("lesson_sessions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("LessonSession", back_populates="records")
    student = relationship("Student", back_populates="attendance_records")

class SMSAlertLog(Base):
    """
    Gönderilen veya simüle edilen SMS bildirim günlüğü.
    """
    __tablename__ = "sms_alert_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    phone = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    risk_score = Column(Float, nullable=True)
    reason = Column(String(255), nullable=True)
    status = Column(String(50), default="SENT")             # SENT, FAILED, MOCKED
    sent_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="sms_logs")

class InterventionNote(Base):
    """
    Rehberlik / danışman öğretmenin veli veya öğrenci ile yaptığı görüşme kayıtları.
    """
    __tablename__ = "intervention_notes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    counselor_name = Column(String(100), nullable=False)
    note = Column(Text, nullable=False)
    action_plan = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="intervention_notes")
