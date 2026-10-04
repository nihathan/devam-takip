from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Student, ClassRoom, Subject, InterventionNote
from ..schemas import (
    StudentCreate, StudentResponse,
    ClassRoomCreate, ClassRoomResponse,
    SubjectCreate, SubjectResponse,
    InterventionCreate, InterventionResponse
)

router = APIRouter(prefix="/api/school", tags=["Okul & Öğrenci Yönetimi"])

# --- Sınıflar ---
@router.get("/classes", response_model=List[ClassRoomResponse])
def get_classes(db: Session = Depends(get_db)):
    classes = db.query(ClassRoom).all()
    results = []
    for c in classes:
        results.append(ClassRoomResponse(
            id=c.id,
            name=c.name,
            grade_level=c.grade_level,
            student_count=len(c.students)
        ))
    return results

@router.post("/classes", response_model=ClassRoomResponse)
def create_class(payload: ClassRoomCreate, db: Session = Depends(get_db)):
    existing = db.query(ClassRoom).filter(ClassRoom.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu isimde bir sınıf zaten mevcut.")
    new_class = ClassRoom(name=payload.name, grade_level=payload.grade_level)
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return ClassRoomResponse(id=new_class.id, name=new_class.name, grade_level=new_class.grade_level, student_count=0)

# --- Dersler ---
@router.get("/subjects", response_model=List[SubjectResponse])
def get_subjects(db: Session = Depends(get_db)):
    return db.query(Subject).all()

@router.post("/subjects", response_model=SubjectResponse)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    existing = db.query(Subject).filter(Subject.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu isimde bir ders zaten mevcut.")
    subject = Subject(name=payload.name, code=payload.code)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

# --- Öğrenciler ---
@router.get("/students", response_model=List[StudentResponse])
def get_students(class_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Student).filter(Student.is_active == True)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    students = query.order_by(Student.last_name, Student.first_name).all()
    
    return [
        StudentResponse(
            id=s.id,
            student_number=s.student_number,
            first_name=s.first_name,
            last_name=s.last_name,
            full_name=s.full_name,
            class_id=s.class_id,
            classroom_name=s.classroom.name if s.classroom else None,
            parent_name=s.parent_name,
            parent_phone=s.parent_phone,
            parent_email=s.parent_email,
            is_active=s.is_active,
            created_at=s.created_at
        )
        for s in students
    ]

@router.post("/students", response_model=StudentResponse)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.student_number == payload.student_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu öğrenci numarası zaten kullanımda.")
    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentResponse(
        id=student.id,
        student_number=student.student_number,
        first_name=student.first_name,
        last_name=student.last_name,
        full_name=student.full_name,
        class_id=student.class_id,
        classroom_name=student.classroom.name if student.classroom else None,
        parent_name=student.parent_name,
        parent_phone=student.parent_phone,
        parent_email=student.parent_email,
        is_active=student.is_active,
        created_at=student.created_at
    )

# --- Rehberlik Müdahale Notları ---
@router.post("/interventions", response_model=InterventionResponse)
def add_intervention(payload: InterventionCreate, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Öğrenci bulunamadı.")
    note = InterventionNote(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
