import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Bed, Hospitalization, Patient


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
            default="utf-8-sig",
            help="Encoding do CSV (default: utf-8-sig).",
        )
        parser.add_argument(
            "--delimiter",
            default=";",
            help="Delimitador do CSV (default: ;).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove todas as internacoes antes de importar.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"Arquivo nao encontrado: {csv_path}"))
            return

        if options["clear"]:
            Hospitalization.objects.all().delete()
            self.stdout.write(self.style.WARNING("Internacoes removidas antes da importacao."))

        def normalize_fieldnames(fieldnames):
            normalized = []
            for index, field in enumerate(fieldnames or []):
                key = (field or "").strip()
                normalized.append(key or f"__blank_{index}")
            return normalized

        def get_first(row, *keys):
            for key in keys:
                value = (row.get(key) or "").strip()
                if value:
                    return value
            return ""

        def parse_date(value):
            if not value:
                return None
            value = value.strip()
            for fmt in ("%d/%m/%Y", "%d/%m/%y"):
                try:
                    return timezone.make_aware(
                        datetime.strptime(value, fmt),
                        timezone.get_current_timezone(),
                    )
                except ValueError:
                    continue
            return None

        def infer_clinic(identifier):
            prefix = (identifier or "").strip().upper()[:1]
            if prefix == "A":
                return "CLÍNICA A"
            if prefix == "B":
                return "CLÍNICA B"
            if prefix == "C":
                return "CLÍNICA C"
            return "EXTRA"

        created_patients = 0
        updated_patients = 0
        created_beds = 0
        updated_beds = 0
        created_hosp = 0
        skipped_rows = 0

        with csv_path.open("r", encoding=options["encoding"], newline="") as f:
            reader = csv.DictReader(f, delimiter=options["delimiter"])
            reader.fieldnames = normalize_fieldnames(reader.fieldnames)

            if "LEITO" not in reader.fieldnames:
                self.stderr.write(self.style.ERROR("CSV nao possui coluna 'LEITO'."))
                return

            with transaction.atomic():
                for row in reader:
                    bed_raw = get_first(row, "LEITO")
                    patient_name = get_first(row, "PACIENTE")
                    if not bed_raw or not patient_name:
                        skipped_rows += 1
                        continue

                    prontuario = get_first(row, "REGISTRO", "PRONTUÁRIO", "PRONTUARIO")
                    admission_raw = get_first(row, "DATA DE ENTRADA", "DATA ADM HOSP ORIGEM", "DATA DE ADMISSÃO", "DATA DE ADMISSAO")
                    procedure_planned = get_first(row, "PROCED")
                    current_status = get_first(row, "CONDUTA")
                    expected_surgery_raw = get_first(row, "PREVISÃO ORTOPÉDICA", "PREVISAO ORTOPAEDICA")
                    date_of_birth_raw = get_first(row, "DATA NASC", "DATA DE NASCIMENTO")
                    diagnosis_raw = get_first(row, "HIPÓTESE DIAGNÓSTICO", "HIPOTESE DIAGNOSTICO")
                    pending_exams_raw = get_first(row, "EXAMES PENDENTES")
                    infected_raw = get_first(row, "INFECTADO")

                    admission_date = parse_date(admission_raw)
                    expected_surgery_date = parse_date(expected_surgery_raw)
                    date_of_birth = parse_date(date_of_birth_raw)

                    bed_obj, bed_created = Bed.objects.update_or_create(
                        identifier=bed_raw,
                        defaults={
                            "clinic": infer_clinic(bed_raw),
                            "category": "INFECTADO" if infected_raw else "NORMAL",
                            "is_active": True,
                        },
                    )
                    if bed_created:
                        created_beds += 1
                    else:
                        updated_beds += 1

                    patient_obj, patient_created = Patient.objects.update_or_create(
                        medical_record_number=prontuario or f"TEMP-{bed_raw}",
                        defaults={
                            "name": patient_name,
                            "date_of_birth": date_of_birth.date() if date_of_birth else None,
                        },
                    )
                    if patient_created:
                        created_patients += 1
                    else:
                        updated_patients += 1

                    Hospitalization.objects.create(
                        patient=patient_obj,
                        bed=bed_obj,
                        admission_date=admission_date or timezone.now(),
                        procedure_planned=procedure_planned or None,
                        expected_surgery_date=expected_surgery_date.date() if expected_surgery_date else None,
                        current_status=current_status or None,
                        hipotese_diagnostica=diagnosis_raw or None,
                        exames_pendentes=pending_exams_raw or None,
                        necessidade_isolamento="Sim" if infected_raw else None,
                    )
                    created_hosp += 1

        self.stdout.write(self.style.SUCCESS(
            "Importacao concluida. "
            f"Pacientes criados: {created_patients}, atualizados: {updated_patients}, "
            f"Leitos criados: {created_beds}, atualizados: {updated_beds}, "
            f"Internacoes criadas: {created_hosp}, linhas ignoradas: {skipped_rows}"
        ))
