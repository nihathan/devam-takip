import os
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import Student, SMSAlertLog
from .risk_analyzer import StudentRiskAnalysis

logger = logging.getLogger("sms_service")

class SMSService:
    @staticmethod
    def generate_smart_message(student_name: str, analysis: StudentRiskAnalysis) -> str:
        """
        Öğrencinin tespit edilen risk faktörlerine göre veliye uygun, yapıcı
        ve bilgilendirici bir SMS metni oluşturur.
        """
        # 1. Hızla artan devamsızlık durumu
        if analysis.recent_absence_count >= 6 and analysis.acceleration_rate > 30:
            return (
                f"Sayın Velimiz, öğrenciniz {student_name}'in son 2 haftada ders devamsızlığı "
                f"hızla artarak {analysis.recent_absence_count} ders saatine ulaşmıştır. "
                f"Öğrencinin ders başarısının olumsuz etkilenmemesi için okulumuz rehberlik servisine başvurmanız rica olunur."
            )
        
        # 2. Cuma / Pazartesi kalıbı
        if any("Pazartesi ve Cuma" in factor for factor in analysis.risk_factors):
            return (
                f"Sayın Velimiz, {student_name}'in özellikle hafta başı ve cuma günleri derslere katılımında "
                f"düzensizlik tespit edilmiştir. Toplam devamsızlığı {analysis.absent_count} saate ulaşmıştır. "
                f"Bilgilerinize sunarız. (Devam Takip)"
            )

        # 3. Kritik eşik aşımı
        if analysis.absent_count >= 20:
            return (
                f"DİKKAT: Sayın Velimiz, {student_name}'in mazeretsiz devamsızlığı {analysis.absent_count} saate "
                f"ulaşarak resmi kritik sınıra yaklaşmıştır. Olası sınıf tekrarı riskine karşı lütfen "
                f"okul idaresiyle ivedilikle iletişime geçiniz."
            )

        # 4. Genel uyarı
        return (
            f"Sayın Velimiz, öğrenciniz {student_name}'in toplam devamsızlık saati {analysis.absent_count} olmuştur "
            f"(Son 14 günde: {analysis.recent_absence_count} ders). Öğrencinin gelişimini birlikte desteklemek adına "
            f"okulumuzla iletişime geçebilirsiniz."
        )

    @staticmethod
    def can_send_sms(student_id: int, db: Session, cooldown_hours: int = 24) -> bool:
        """
        Aynı veliye son 24 saat içinde tekrar SMS gönderilip bıkkınlık (spam)
        yaratılmasını engeller.
        """
        threshold = datetime.utcnow() - timedelta(hours=cooldown_hours)
        recent_log = (
            db.query(SMSAlertLog)
            .filter(SMSAlertLog.student_id == student_id, SMSAlertLog.sent_at >= threshold)
            .first()
        )
        return recent_log is None

    @classmethod
    def send_alert(
        cls,
        student: Student,
        analysis: StudentRiskAnalysis,
        db: Session,
        custom_message: str = None,
        force: bool = False
    ) -> SMSAlertLog:
        """
        Veliye SMS gönderir ve sistem günlüğüne kaydeder.
        """
        if not force and not cls.can_send_sms(student.id, db):
            logger.info(f"Öğrenci {student.id} için son 24 saatte zaten SMS gönderilmiş. Atlandı.")
            # Yine de log için veya bilgi için durum döndürülebilir
        
        message_body = custom_message or cls.generate_smart_message(student.full_name, analysis)
        
        # Gerçek ortamda burası Netgsm / Twilio / Mutlucell API'sine bağlanır.
        # Geliştirme ortamında Mock olarak çalışır ve konsola/veritabanına yazar.
        provider_status = "SENT_MOCKED"
        print(f"\n[SMS GONDERILDI] -> {student.parent_phone} ({student.parent_name})")
        print(f"Mesaj: {message_body}\n")

        sms_log = SMSAlertLog(
            student_id=student.id,
            phone=student.parent_phone,
            message=message_body,
            risk_score=analysis.risk_score,
            reason=", ".join(analysis.risk_factors) if analysis.risk_factors else "Rutin Takip",
            status=provider_status,
            sent_at=datetime.utcnow()
        )
        db.add(sms_log)
        db.commit()
        db.refresh(sms_log)
        return sms_log
