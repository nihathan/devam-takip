from typing import List, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Student, AttendanceRecord, LessonSession, SMSAlertLog, RiskLevel, AttendanceStatus
from ..schemas import (
    StudentRiskAnalysis, OverviewStatistics,
    SendSMSRequest, SMSAlertLogResponse
)
from ..services.risk_analyzer import analyze_student_risk, calculate_overview_kpis
from ..services.sms_service import SMSService

router = APIRouter(prefix="/api/analytics", tags=["Risk Analizi & SMS Erken Uyarı"])

@router.get("/overview", response_model=OverviewStatistics)
def get_overview(db: Session = Depends(get_db)):
    """
    Okul geneli temel metrikler, devam oranı ve risk grupları dağılımı.
    """
    return calculate_overview_kpis(db)

@router.get("/risk-report", response_model=List[StudentRiskAnalysis])
def get_risk_report(
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    level: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL"),
    class_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Risk puanına göre sıralanmış öğrenci listesi ve erken uyarı faktörleri.
    """
    query = db.query(Student).filter(Student.is_active == True)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    students = query.all()

    analyses: List[StudentRiskAnalysis] = []
    for student in students:
        res = analyze_student_risk(student, db)
        if res.risk_score >= min_score:
            if level and res.risk_level.value != level:
                continue
            analyses.append(res)

    # Risk puanına göre çoktan aza sırala
    analyses.sort(key=lambda x: x.risk_score, reverse=True)
    return analyses

@router.get("/student/{student_id}", response_model=StudentRiskAnalysis)
def get_student_risk(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı.")
    return analyze_student_risk(student, db)

@router.get("/heatmaps")
def get_heatmaps(db: Session = Depends(get_db)):
    """
    Ders saatlerine ve haftanın günlerine göre devamsızlık yoğunluk haritası.
    Hangi saatlerde veya günlerde kaçışın yoğun olduğunu gösterir.
    """
    records = (
        db.query(AttendanceRecord, LessonSession)
        .join(LessonSession, AttendanceRecord.session_id == LessonSession.id)
        .filter(AttendanceRecord.status == AttendanceStatus.ABSENT)
        .all()
    )

    days_map = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma"}
    day_distribution = {name: 0 for name in days_map.values()}
    hour_distribution = {f"{h}. Ders": 0 for h in range(1, 9)}

    for rec, sess in records:
        w_day = sess.session_date.weekday()
        if w_day in days_map:
            day_distribution[days_map[w_day]] += 1
        h_str = f"{sess.lesson_hour}. Ders"
        if h_str in hour_distribution:
            hour_distribution[h_str] += 1

    return {
        "day_distribution": day_distribution,
        "hour_distribution": hour_distribution,
        "total_unexcused_hours": len(records)
    }

@router.post("/send-alert", response_model=SMSAlertLogResponse)
def trigger_sms_alert(payload: SendSMSRequest, force: bool = False, db: Session = Depends(get_db)):
    """
    Belirli bir öğrencinin velisine analiz özetini veya özel mesajı SMS olarak iletir.
    """
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı.")

    analysis = analyze_student_risk(student, db)
    log_entry = SMSService.send_alert(
        student=student,
        analysis=analysis,
        db=db,
        custom_message=payload.custom_message,
        force=force
    )

    return SMSAlertLogResponse(
        id=log_entry.id,
        student_id=student.id,
        student_name=student.full_name,
        phone=log_entry.phone,
        message=log_entry.message,
        risk_score=log_entry.risk_score,
        reason=log_entry.reason,
        status=log_entry.status,
        sent_at=log_entry.sent_at
    )

@router.post("/auto-alert-critical")
def trigger_batch_critical_alerts(db: Session = Depends(get_db)):
    """
    Kritik risk seviyesindeki (CRITICAL) tüm öğrencilerin velilerine toplu akıllı SMS gönderir.
    (24 saatlik spam filtresi otomatik uygulanır)
    """
    students = db.query(Student).filter(Student.is_active == True).all()
    sent_count = 0
    skipped_count = 0

    for student in students:
        analysis = analyze_student_risk(student, db)
        if analysis.risk_level == RiskLevel.CRITICAL:
            if SMSService.can_send_sms(student.id, db):
                SMSService.send_alert(student, analysis, db)
                sent_count += 1
            else:
                skipped_count += 1

    return {
        "success": True,
        "sent_count": sent_count,
        "skipped_recently_sent": skipped_count,
        "message": f"{sent_count} kritik öğrenci velisine SMS uyarısı gönderildi."
    }

@router.get("/sms-logs", response_model=List[SMSAlertLogResponse])
def get_sms_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(SMSAlertLog).order_by(SMSAlertLog.sent_at.desc()).limit(limit).all()
    results = []
    for l in logs:
        results.append(SMSAlertLogResponse(
            id=l.id,
            student_id=l.student_id,
            student_name=l.student.full_name if l.student else "Silinmiş",
            phone=l.phone,
            message=l.message,
            risk_score=l.risk_score,
            reason=l.reason,
            status=l.status,
            sent_at=l.sent_at
        ))
    return results
