from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from ..models import Student, AttendanceRecord, LessonSession, AttendanceStatus, RiskLevel, Subject, ClassRoom
from ..schemas import StudentRiskAnalysis, OverviewStatistics

def analyze_student_risk(student: Student, db: Session, reference_date: date = None) -> StudentRiskAnalysis:
    """
    Belirli bir öğrencinin devam-devamsızlık verilerini analiz ederek
    risk puanını, erken uyarı faktörlerini ve trend ivmesini hesaplar.
    """
    if reference_date is None:
        reference_date = date.today()

    records = (
        db.query(AttendanceRecord, LessonSession, Subject)
        .join(LessonSession, AttendanceRecord.session_id == LessonSession.id)
        .join(Subject, LessonSession.subject_id == Subject.id)
        .filter(AttendanceRecord.student_id == student.id)
        .order_by(LessonSession.session_date.asc(), LessonSession.lesson_hour.asc())
        .all()
    )

    total_sessions = len(records)
    absent_count = 0
    late_count = 0
    excused_count = 0

    # Tarihsel pencereler (Son 14 gün vs önceki 14 gün)
    fourteen_days_ago = reference_date - timedelta(days=14)
    twenty_eight_days_ago = reference_date - timedelta(days=28)

    recent_absent = 0
    prior_absent = 0

    day_of_week_counts = defaultdict(int) # 0: Pazartesi, 4: Cuma vb.
    hour_counts = defaultdict(int)        # 1. ders, 2. ders vb.
    subject_counts = defaultdict(int)     # Ders adı -> devamsızlık sayısı

    for record, session, subject in records:
        if record.status == AttendanceStatus.ABSENT:
            absent_count += 1
            s_date = session.session_date
            
            # Son 14 gün ve önceki 14 gün karşılaştırması
            if s_date >= fourteen_days_ago:
                recent_absent += 1
            elif twenty_eight_days_ago <= s_date < fourteen_days_ago:
                prior_absent += 1

            # Gün ve saat analizi
            day_of_week_counts[s_date.weekday()] += 1
            hour_counts[session.lesson_hour] += 1
            subject_counts[subject.name] += 1

        elif record.status == AttendanceStatus.LATE:
            late_count += 1
        elif record.status == AttendanceStatus.EXCUSED:
            excused_count += 1

    # 1. İvme (Hızlanma) Hesabı
    acceleration_rate = 0.0
    if prior_absent > 0:
        acceleration_rate = round(((recent_absent - prior_absent) / prior_absent) * 100, 1)
    elif recent_absent > 0:
        acceleration_rate = 100.0 # Önceki dönem sıfırken birden devamsızlık başladı

    # 2. Risk Skoru Hesabı (0 - 100)
    # Temel bileşenler:
    # - Toplam devamsızlık saati (örneğin 30 saat ve üzeri MEB sınırlarına yaklaşır)
    # - Son 2 haftalık ivme
    # - Geç kalmalar (3 geç kalma ~ 1 devamsızlık ağırlığı)
    base_absence_score = min(50.0, (absent_count / 30.0) * 50.0)
    
    recent_velocity_score = 0.0
    if recent_absent >= 6: # Son 2 haftada 6+ saat devamsızlık ciddi uyarıdır
        recent_velocity_score = min(30.0, (recent_absent / 10.0) * 30.0)
    elif recent_absent >= 3:
        recent_velocity_score = 15.0

    tardiness_score = min(10.0, (late_count / 6.0) * 10.0)

    risk_factors = []

    # Risk Faktörleri ve Puan Ekleme
    # Cuma / Pazartesi analizi (Hafta sonu uzatma eğilimi)
    friday_monday_absences = day_of_week_counts[0] + day_of_week_counts[4]
    if absent_count >= 4 and friday_monday_absences / absent_count >= 0.5:
        risk_factors.append("Pazartesi ve Cuma günlerinde yoğun devamsızlık (%{:.0f})".format(
            (friday_monday_absences / absent_count) * 100
        ))
        base_absence_score = min(50.0, base_absence_score + 5.0)

    # İvme faktörü
    if recent_absent >= 4 and acceleration_rate >= 50.0:
        risk_factors.append(f"Son 2 haftada devamsızlık hızla artışta (+%{acceleration_rate})")

    # Ders bazlı odaklanma analizi
    for subj_name, count in subject_counts.items():
        if count >= 3 and count / max(1, absent_count) >= 0.4:
            risk_factors.append(f"'{subj_name}' dersine katılım belirgin şekilde düşük ({count} saat)")

    # İlk ders veya son ders kaçırma analizi
    first_hour_absent = hour_counts[1]
    if first_hour_absent >= 3 and first_hour_absent / max(1, absent_count) >= 0.35:
        risk_factors.append(f"Sabah 1. dersleri kaçırma / geç kalma eğilimi ({first_hour_absent} kez)")

    if absent_count >= 20:
        risk_factors.append(f"Toplam kritik devamsızlık sınırına yaklaşıyor ({absent_count} saat)")

    total_risk_score = round(min(100.0, base_absence_score + recent_velocity_score + tardiness_score), 1)

    # Risk Seviyesi Belirleme
    if total_risk_score >= 70.0 or absent_count >= 25:
        risk_level = RiskLevel.CRITICAL
    elif total_risk_score >= 45.0 or recent_absent >= 6:
        risk_level = RiskLevel.HIGH
    elif total_risk_score >= 25.0:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    classroom_name = student.classroom.name if student.classroom else "Bilinmiyor"

    return StudentRiskAnalysis(
        student_id=student.id,
        student_number=student.student_number,
        student_name=student.full_name,
        classroom_name=classroom_name,
        parent_name=student.parent_name,
        parent_phone=student.parent_phone,
        total_sessions=total_sessions,
        absent_count=absent_count,
        late_count=late_count,
        excused_count=excused_count,
        recent_absence_count=recent_absent,
        prior_absence_count=prior_absent,
        acceleration_rate=acceleration_rate,
        risk_score=total_risk_score,
        risk_level=risk_level,
        risk_factors=risk_factors,
        subject_breakdown=dict(subject_counts)
    )

def calculate_overview_kpis(db: Session) -> OverviewStatistics:
    """
    Tüm okul için genel KPI ve devam-devamsızlık özet istatistiklerini hesaplar.
    """
    from ..models import SMSAlertLog

    students = db.query(Student).filter(Student.is_active == True).all()
    total_students = len(students)
    total_classes = db.query(ClassRoom).count()
    total_sessions = db.query(LessonSession).count()
    total_sms = db.query(SMSAlertLog).count()

    total_records = db.query(AttendanceRecord).count()
    present_records = db.query(AttendanceRecord).filter(
        AttendanceRecord.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.EXCUSED])
    ).count()

    overall_attendance_rate = 100.0
    if total_records > 0:
        overall_attendance_rate = round((present_records / total_records) * 100, 1)

    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0

    for student in students:
        analysis = analyze_student_risk(student, db)
        if analysis.risk_level == RiskLevel.CRITICAL:
            critical_count += 1
        elif analysis.risk_level == RiskLevel.HIGH:
            high_count += 1
        elif analysis.risk_level == RiskLevel.MEDIUM:
            medium_count += 1
        else:
            low_count += 1

    return OverviewStatistics(
        total_students=total_students,
        total_classes=total_classes,
        total_sessions=total_sessions,
        overall_attendance_rate=overall_attendance_rate,
        critical_risk_count=critical_count,
        high_risk_count=high_count,
        medium_risk_count=medium_count,
        low_risk_count=low_count,
        total_sms_sent=total_sms
    )
