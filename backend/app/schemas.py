from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .models import AttendanceStatus, RiskLevel

# --- Sınıf Şemaları ---
class ClassRoomBase(BaseModel):
    name: str
    grade_level: int

class ClassRoomCreate(ClassRoomBase):
    pass

class ClassRoomResponse(ClassRoomBase):
    id: int
    student_count: Optional[int] = 0

    class Config:
        from_attributes = True

# --- Ders Şemaları ---
class SubjectBase(BaseModel):
    name: str
    code: Optional[str] = None

class SubjectCreate(SubjectBase):
    pass

class SubjectResponse(SubjectBase):
    id: int

    class Config:
        from_attributes = True

# --- Öğrenci Şemaları ---
class StudentBase(BaseModel):
    student_number: str
    first_name: str
    last_name: str
    class_id: int
    parent_name: str
    parent_phone: str
    parent_email: Optional[str] = None
    is_active: bool = True

class StudentCreate(StudentBase):
    pass

class StudentResponse(StudentBase):
    id: int
    full_name: str
    classroom_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Yoklama Şemaları ---
class SingleAttendanceEntry(BaseModel):
    student_id: int
    status: AttendanceStatus = AttendanceStatus.PRESENT
    note: Optional[str] = None

class BulkAttendanceCreate(BaseModel):
    class_id: int
    subject_id: int
    session_date: date
    lesson_hour: int
    entries: List[SingleAttendanceEntry]

class AttendanceRecordResponse(BaseModel):
    id: int
    session_id: int
    student_id: int
    student_name: Optional[str] = None
    status: AttendanceStatus
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Erken Uyarı ve Risk Analiz Şemaları ---
class StudentRiskAnalysis(BaseModel):
    student_id: int
    student_number: str
    student_name: str
    classroom_name: str
    parent_name: str
    parent_phone: str
    total_sessions: int
    absent_count: int           # Özürsüz devamsızlık saati
    late_count: int             # Geç kalma sayısı
    excused_count: int          # İzinli/raporlu saat
    recent_absence_count: int   # Son 14 gündeki devamsızlık
    prior_absence_count: int    # Önceki 14 gündeki devamsızlık
    acceleration_rate: float    # Artış ivmesi yüzdesi
    risk_score: float           # 0 - 100
    risk_level: RiskLevel
    risk_factors: List[str]     # ["Cuma günleri yoğunluk", "Son 2 haftada ani artış"]
    subject_breakdown: Dict[str, int] # En çok kaçırılan dersler

class OverviewStatistics(BaseModel):
    total_students: int
    total_classes: int
    total_sessions: int
    overall_attendance_rate: float
    critical_risk_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    total_sms_sent: int

# --- SMS Şemaları ---
class SendSMSRequest(BaseModel):
    student_id: int
    custom_message: Optional[str] = None

class SMSAlertLogResponse(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    phone: str
    message: str
    risk_score: Optional[float] = None
    reason: Optional[str] = None
    status: str
    sent_at: datetime

    class Config:
        from_attributes = True

# --- Görüşme / Rehberlik Notu ---
class InterventionCreate(BaseModel):
    student_id: int
    counselor_name: str
    note: str
    action_plan: Optional[str] = None

class InterventionResponse(InterventionCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
