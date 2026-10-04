from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import LessonSession, AttendanceRecord, Student, ClassRoom, Subject, AttendanceStatus
from ..schemas import BulkAttendanceCreate, AttendanceRecordResponse

router = APIRouter(prefix="/api/attendance", tags=["Yoklama İşlemleri"])

@router.post("/bulk")
def save_bulk_attendance(payload: BulkAttendanceCreate, db: Session = Depends(get_db)):
    """
    Belirli bir tarih, ders saati, sınıf ve ders için toplu yoklama kaydeder.
    Eğer aynı oturum daha önce kaydedilmişse üzerine günceller.
    """
    # Oturum var mı kontrol et veya oluştur
    session = (
        db.query(LessonSession)
        .filter(
            LessonSession.class_id == payload.class_id,
            LessonSession.subject_id == payload.subject_id,
            LessonSession.session_date == payload.session_date,
            LessonSession.lesson_hour == payload.lesson_hour
        )
        .first()
    )

    if not session:
        session = LessonSession(
            class_id=payload.class_id,
            subject_id=payload.subject_id,
            session_date=payload.session_date,
            lesson_hour=payload.lesson_hour
        )
        db.add(session)
        db.flush()

    # Mevcut kayıtları temizle ve yenilerini ekle (idempotent güncelleme)
    db.query(AttendanceRecord).filter(AttendanceRecord.session_id == session.id).delete()

    created_count = 0
    for entry in payload.entries:
        record = AttendanceRecord(
            session_id=session.id,
            student_id=entry.student_id,
            status=entry.status,
            note=entry.note
        )
        db.add(record)
        created_count += 1

    db.commit()
    return {
        "success": True,
        "session_id": session.id,
        "recorded_students": created_count,
        "message": f"{payload.session_date} {payload.lesson_hour}. ders yoklaması başarıyla kaydedildi."
    }

@router.get("/sessions")
def get_recent_sessions(
    class_id: Optional[int] = None,
    limit: int = 15,
    db: Session = Depends(get_db)
):
    query = db.query(LessonSession)
    if class_id:
        query = query.filter(LessonSession.class_id == class_id)
    sessions = query.order_by(LessonSession.session_date.desc(), LessonSession.lesson_hour.desc()).limit(limit).all()

    results = []
    for s in sessions:
        present_c = sum(1 for r in s.records if r.status == AttendanceStatus.PRESENT)
        absent_c = sum(1 for r in s.records if r.status == AttendanceStatus.ABSENT)
        results.append({
            "session_id": s.id,
            "class_name": s.classroom.name,
            "subject_name": s.subject.name,
            "date": s.session_date.isoformat(),
            "lesson_hour": s.lesson_hour,
            "total_students": len(s.records),
            "present_count": present_c,
            "absent_count": absent_c
        })
    return results

@router.get("/student/{student_id}")
def get_student_attendance_history(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı.")
    
    records = (
        db.query(AttendanceRecord, LessonSession, Subject)
        .join(LessonSession, AttendanceRecord.session_id == LessonSession.id)
        .join(Subject, LessonSession.subject_id == Subject.id)
        .filter(AttendanceRecord.student_id == student_id)
        .order_by(LessonSession.session_date.desc(), LessonSession.lesson_hour.desc())
        .all()
    )

    history = []
    for rec, sess, subj in records:
        history.append({
            "date": sess.session_date.isoformat(),
            "lesson_hour": sess.lesson_hour,
            "subject": subj.name,
            "status": rec.status.value,
            "note": rec.note
        })
    return {
        "student_name": student.full_name,
        "student_number": student.student_number,
        "total_records": len(history),
        "history": history
    }
