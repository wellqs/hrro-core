from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Patient, PatientExtra, ReceptionAttendance, ReceptionQueueEntry


class Command(BaseCommand):
    help = "Cria um paciente de teste e abre um atendimento na Recepção, inserindo na fila."

    def handle(self, *args, **options):
        patient, created = Patient.objects.get_or_create(
            medical_record_number="E2E-0001",
            defaults={
                "name": "Paciente Teste Recepção",
                "date_of_birth": None,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Paciente criado: {patient}"))
        else:
            self.stdout.write(self.style.WARNING(f"Paciente reutilizado: {patient}"))

        PatientExtra.objects.get_or_create(patient=patient)

        attendance = ReceptionAttendance.objects.create(
            patient=patient,
            origin_sector="Recepção",
            care_type="AMBULATORIO",
            origin="HOSPITAL",
            reason="Dor abdominal há 2 dias",
            referral_type="ESPONTANEO",
            reference_document="TEST-REF-001",
            entry_at=timezone.now(),
            triage_at=timezone.now(),
            attendance_at=None,
            requester_name="Dr. Exemplo",
            requester_registry="CRM-0000",
            notes="Fluxo e2e automático.",
        )

        entry = ReceptionQueueEntry.objects.create(
            attendance=attendance,
            destination_sector="Ambulatório",
            priority="NORMAL",
            status="AGUARDANDO",
        )

        self.stdout.write(self.style.SUCCESS("Atendimento aberto e inserido na fila."))
        self.stdout.write(
            f"Fila ID={entry.id} | Paciente={patient.name} | Destino={entry.destination_sector} | Prioridade={entry.get_priority_display()} | Status={entry.get_status_display()}"
        )

