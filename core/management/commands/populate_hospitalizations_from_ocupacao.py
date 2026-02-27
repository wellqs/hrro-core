import csv
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand

from core.models import Bed, Patient, Hospitalization


class Command(BaseCommand):
    help = "Popula internacoes a partir do arquivo ocupacao.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default="ocupacao.csv",
            help="Caminho do arquivo CSV (default: ocupacao.csv).",
        )
        parser.add_argument(
            "--encoding",
            default="latin-1",
            help="Encoding do CSV (default: latin-1).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove todas as internacoes ativas antes de importar.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"Arquivo nao encontrado: {csv_path}"))
            return

        if options["clear"]:
            Hospitalization.objects.all().delete()
            self.stdout.write(self.style.WARNING("Internacoes removidas antes da importacao."))

        def parse_date(value):
            if not value:
                return None
            value = value.strip()
            for fmt in ("%d/%m/%Y", "%d/%m/%y"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            return None

        created_patients = 0
        created_beds = 0
        created_hosp = 0

        with csv_path.open("r", encoding=options["encoding"], newline="") as f:
            reader = csv.DictReader(f)
            if "LEITO" not in reader.fieldnames:
                self.stderr.write(self.style.ERROR("CSV nao possui coluna 'LEITO'."))
                return

            for row in reader:
                bed_raw = (row.get("LEITO") or "").strip()
                if not bed_raw:
                    continue

                patient_name = (row.get("PACIENTE") or "").strip()
                if not patient_name:
                    continue

                prontuario = (row.get("PRONTUÁRIO") or row.get("PRONTUARIO") or "").strip()
                admission_raw = (row.get("DATA DE ADMISSÃO") or row.get("DATA DE ADMISSAO") or "").strip()
                procedure_planned = (row.get("PROCED") or row.get("HIPÓTESE DIAGNÓSTICO") or row.get("HIPOTESE DIAGNOSTICO") or "").strip()
                current_status = (row.get("CONDUTA") or "").strip()
                expected_surgery_raw = (row.get("PREVISAO ORTOPAÉDICA") or row.get("PREVISAO ORTOPAEDICA") or "").strip()

                admission_date = parse_date(admission_raw)
                expected_surgery_date = parse_date(expected_surgery_raw)

                # Bed
                bed_obj = Bed.objects.filter(identifier=bed_raw).first()
                if not bed_obj:
                    clinic = bed_raw.split("/")[0].strip()
                    bed_obj = Bed.objects.create(
                        identifier=bed_raw,
                        clinic=clinic,
                        category="NORMAL",
                        is_active=True,
                    )
                    created_beds += 1

                # Patient
                if prontuario:
                    patient_obj = Patient.objects.filter(medical_record_number=prontuario).first()
                else:
                    patient_obj = None
                if not patient_obj:
                    if not prontuario:
                        # fallback: use name as unique-ish key (no guarantee)
                        existing = Patient.objects.filter(name=patient_name).first()
                        if existing:
                            patient_obj = existing
                        else:
                            patient_obj = Patient.objects.create(
                                name=patient_name,
                                medical_record_number=f"TEMP-{bed_raw}",
                            )
                            created_patients += 1
                    else:
                        patient_obj = Patient.objects.create(
                            name=patient_name,
                            medical_record_number=prontuario,
                        )
                        created_patients += 1

                # Hospitalization
                Hospitalization.objects.create(
                    patient=patient_obj,
                    bed=bed_obj,
                    admission_date=admission_date or datetime.now(),
                    procedure_planned=procedure_planned or None,
                    expected_surgery_date=expected_surgery_date.date() if expected_surgery_date else None,
                    current_status=current_status or None,
                )
                created_hosp += 1

        self.stdout.write(self.style.SUCCESS(
            f"Importacao concluida. Pacientes: {created_patients}, Leitos: {created_beds}, Internacoes: {created_hosp}"
        ))
