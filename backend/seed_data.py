import random
from datetime import date, timedelta
from app.database import SessionLocal, engine, Base
from app.models import ClassRoom, Subject, Student, LessonSession, AttendanceRecord, AttendanceStatus, SMSAlertLog

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Eğer zaten veri varsa tekrar ekleme
    if db.query(Student).count() > 0:
        print("[INFO] Veritabaninda zaten kayit mevcut. Seed adimi atlandi.")
        db.close()
        return

    print("[START] Baslangic demo verileri yukleniyor...")

    # 1. Sınıflar
    class_10a = ClassRoom(name="10-A", grade_level=10)
    class_10b = ClassRoom(name="10-B", grade_level=10)
    class_11a = ClassRoom(name="11-A", grade_level=11)
    db.add_all([class_10a, class_10b, class_11a])
    db.flush()

    # 2. Dersler
    subjects = [
        Subject(name="Matematik", code="MAT"),
        Subject(name="Fizik", code="FIZ"),
        Subject(name="Türk Dili ve Edebiyatı", code="EDB"),
        Subject(name="Tarih", code="TAR"),
        Subject(name="İngilizce", code="ING"),
        Subject(name="Biyoloji", code="BIY"),
    ]
    db.add_all(subjects)
    db.flush()

    # 3. Öğrenciler (Gerçekçi profiller)
    students_data = [
        # (Ad, Soyad, Sınıf, No, Veli Ad, Veli Tel, Risk Senaryosu)
        ("Ali", "Kaya", class_10a, "101", "Mehmet Kaya", "+905321001001", "CRITICAL_ACCELERATING"),
        ("Ayşe", "Demir", class_10a, "102", "Fatma Demir", "+905321001002", "FRIDAY_MONDAY"),
        ("Burak", "Çelik", class_10a, "103", "Kemal Çelik", "+905321001003", "MATH_FOCUSED"),
        ("Ceren", "Yılmaz", class_10a, "104", "Ahmet Yılmaz", "+905321001004", "FIRST_HOUR_LATE"),
        ("Deniz", "Öztürk", class_10a, "105", "Zeynep Öztürk", "+905321001005", "EXCELLENT"),
        ("Ece", "Şahin", class_10a, "106", "Hüseyin Şahin", "+905321001006", "EXCELLENT"),
        ("Furkan", "Koç", class_10a, "107", "Sevgi Koç", "+905321001007", "MODERATE"),
        ("Gizem", "Aydın", class_10b, "201", "Murat Aydın", "+905321002001", "CRITICAL_HIGH"),
        ("Hakan", "Arslan", class_10b, "202", "Selin Arslan", "+905321002002", "EXCELLENT"),
        ("İrem", "Kurt", class_10b, "203", "Emre Kurt", "+905321002003", "EXCELLENT"),
        ("Kerem", "Tekin", class_11a, "301", "Mustafa Tekin", "+905321003001", "MODERATE"),
        ("Leyla", "Polat", class_11a, "302", "Gül Polat", "+905321003002", "EXCELLENT")
    ]

    student_objects = []
    student_scenarios = {}
    for first, last, cls, no, p_name, p_tel, scen in students_data:
        st = Student(
            student_number=no,
            first_name=first,
            last_name=last,
            class_id=cls.id,
            parent_name=p_name,
            parent_phone=p_tel,
            parent_email=f"{first.lower()}.veli@example.com"
        )
        db.add(st)
        student_objects.append(st)
        student_scenarios[no] = scen

    db.flush()

    # 4. Son 30 günün ders oturumları ve yoklamaları
    today = date.today()
    start_date = today - timedelta(days=28)
    cur_date = start_date

    while cur_date <= today:
        # Hafta sonlarını atla (Pazartesi=0 ... Cuma=4)
        if cur_date.weekday() < 5:
            # Günde 4 oturum oluşturalım
            for hour in range(1, 5):
                for cls in [class_10a, class_10b, class_11a]:
                    subj = subjects[(hour + cur_date.day) % len(subjects)]
                    session = LessonSession(
                        class_id=cls.id,
                        subject_id=subj.id,
                        session_date=cur_date,
                        lesson_hour=hour
                    )
                    db.add(session)
                    db.flush()

                    # Bu sınıftaki öğrencilere senaryoya göre yoklama yaz
                    cls_students = [s for s in student_objects if s.class_id == cls.id]
                    for s in cls_students:
                        scen = student_scenarios[s.student_number]
                        status = AttendanceStatus.PRESENT
                        days_diff = (today - cur_date).days

                        if scen == "CRITICAL_ACCELERATING":
                            # Son 14 günde hızla devamsızlığı artan öğrenci
                            if days_diff <= 14:
                                if random.random() < 0.65:
                                    status = AttendanceStatus.ABSENT
                            else:
                                if random.random() < 0.1:
                                    status = AttendanceStatus.ABSENT

                        elif scen == "FRIDAY_MONDAY":
                            # Pazartesi ve Cuma günleri kaçan
                            if cur_date.weekday() in [0, 4] and random.random() < 0.7:
                                status = AttendanceStatus.ABSENT
                            elif random.random() < 0.05:
                                status = AttendanceStatus.ABSENT

                        elif scen == "MATH_FOCUSED":
                            # Matematik dersini kaçıran
                            if subj.name == "Matematik" and random.random() < 0.8:
                                status = AttendanceStatus.ABSENT
                            elif random.random() < 0.05:
                                status = AttendanceStatus.ABSENT

                        elif scen == "FIRST_HOUR_LATE":
                            # 1. saatte geç kalan veya kaçan
                            if hour == 1:
                                if random.random() < 0.5:
                                    status = AttendanceStatus.LATE
                                elif random.random() < 0.3:
                                    status = AttendanceStatus.ABSENT

                        elif scen == "CRITICAL_HIGH":
                            # Genel yüksek devamsızlık
                            if random.random() < 0.45:
                                status = AttendanceStatus.ABSENT

                        elif scen == "MODERATE":
                            if random.random() < 0.12:
                                status = AttendanceStatus.ABSENT
                            elif random.random() < 0.05:
                                status = AttendanceStatus.LATE

                        else: # EXCELLENT
                            if random.random() < 0.02:
                                status = AttendanceStatus.LATE

                        rec = AttendanceRecord(
                            session_id=session.id,
                            student_id=s.id,
                            status=status
                        )
                        db.add(rec)

        cur_date += timedelta(days=1)

    # 5. Örnek bir ilk SMS logu
    sample_student = student_objects[0]
    sample_log = SMSAlertLog(
        student_id=sample_student.id,
        phone=sample_student.parent_phone,
        message=f"Sayın Velimiz, öğrenciniz {sample_student.full_name}'in son 2 haftada ders devamsızlığı hızla artarak 8 ders saatine ulaşmıştır. Bilginize.",
        risk_score=85.5,
        reason="Son 2 haftada ani artış (+%150)",
        status="SENT_MOCKED"
    )
    db.add(sample_log)

    db.commit()
    db.close()
    print("[SUCCESS] Demo veriler basariyla olusturuldu! Sistem analize hazir.")

if __name__ == "__main__":
    seed()
