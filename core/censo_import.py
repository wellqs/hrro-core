"""
censo_import.py
---------------
Lógica compartilhada de importação do Censo Nominal (CSV KANBAN).
Utilizada pela view de upload e pelo management command.
"""

import csv
import io
import re
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.models import Bed, Hospitalization, Patient

VACANT_LABELS = {
    "VAGO", "VAGO-ISOLAMENTO", "ESTABILIZAÇÃO", "RESERVADO", "-", "",
    "TRIAGEM",
}

BED_ID_RE = re.compile(
    r"^([A-C]\s+\d+\s*/\s*\d+|[\d.]+\s+EXTRA)$", re.IGNORECASE
)

SECTION_CATEGORY = {
    "CLÍNICA A": ("CLÍNICA A", "NORMAL"),
    "EXTENSÃO": ("EXTENSÃO", "EXTENSAO"),
    "CLÍNICA A - INFECTADOS": ("CLÍNICA A - INFECTADOS", "INFECTADO"),
    "CLÍNICA B": ("CLÍNICA B", "NORMAL"),
    "CLÍNICA C": ("CLÍNICA C", "NORMAL"),
}


def _clean(value: str) -> str:
    return (value or "").strip()


def _parse_date(raw: str):
    raw = _clean(raw)
    if not raw:
        return None
    match = re.search(r"\d{2}/\d{2}/\d{4}", raw)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_datetime(raw: str):
    d = _parse_date(raw)
    if d is None:
        return None
    return timezone.make_aware(datetime.combine(d, datetime.min.time()))


def parse_censo_csv(file_obj, encoding="utf-8-sig"):
    """
    Lê um arquivo CSV de Censo Nominal e retorna lista de dicts com os dados
    de cada leito encontrado.

    Aceita file_obj como arquivo aberto em modo binário ou texto, ou bytes.
    """
    if isinstance(file_obj, (bytes, bytearray)):
        text = file_obj.decode(encoding, errors="replace")
        reader = csv.reader(io.StringIO(text))
    else:
        # Django InMemoryUploadedFile / TemporaryUploadedFile → bytes
        raw = file_obj.read()
        if isinstance(raw, bytes):
            text = raw.decode(encoding, errors="replace")
        else:
            text = raw
        reader = csv.reader(io.StringIO(text))

    current_clinic = "CLÍNICA A"
    current_category = "NORMAL"
    rows = []

    for row in reader:
        while len(row) < 30:
            row.append("")

        bed_id = _clean(row[2])
        if not BED_ID_RE.match(bed_id):
            continue

        section_raw = _clean(row[1]).upper().replace("  ", " ")
        for known, (clinic_name, cat) in SECTION_CATEGORY.items():
            if section_raw == known.upper():
                current_clinic = clinic_name
                current_category = cat
                break

        rows.append({
            "bed_id": bed_id,
            "clinic": current_clinic,
            "category": current_category,
            "admission_hrro_raw": _clean(row[5]),
            "registro": _clean(row[6]),
            "patient_name": _clean(row[7]),
            "date_of_birth_raw": _clean(row[9]),
            "diagnosis": _clean(row[12]),
            "conduct": _clean(row[13]),
            "expected_surgery_raw": _clean(row[15]),
            "exams_pending": _clean(row[16]),
            "specialty": _clean(row[19]),
            "infected": _clean(row[25]).upper() == "SIM",
            "cautela": _clean(row[26]),
        })

    return rows


def import_censo(rows, sync_hosp=False):
    """
    Persiste os dados de leitos/pacientes/internações no banco.

    Retorna dict com estatísticas da importação.
    """
    stats = {
        "beds_created": 0,
        "beds_updated": 0,
        "patients_created": 0,
        "patients_updated": 0,
        "hosp_created": 0,
        "hosp_closed": 0,
        "vacant_beds": 0,
        "total_rows": len(rows),
    }

    with transaction.atomic():
        if sync_hosp:
            closed = Hospitalization.objects.filter(
                discharge_date__isnull=True
            ).update(discharge_date=timezone.now())
            stats["hosp_closed"] = closed

        for row in rows:
            bed_id = row["bed_id"]
            cautela = row["cautela"].upper()

            category = row["category"]
            if row["infected"] or "ISOLAMENTO" in cautela or "PRECAUÇÃO" in cautela:
                category = "INFECTADO"
            if "EXTRA" in bed_id.upper():
                category = "EXTRA"
            if "EXTENSÃO" in row["clinic"].upper():
                category = "EXTENSAO"

            bed_obj, bed_created = Bed.objects.update_or_create(
                identifier=bed_id,
                defaults={
                    "clinic": row["clinic"],
                    "category": category,
                    "is_active": True,
                },
            )
            if bed_created:
                stats["beds_created"] += 1
            else:
                stats["beds_updated"] += 1

            patient_name = row["patient_name"]
            registro = row["registro"]
            if patient_name.upper() in VACANT_LABELS or not registro:
                stats["vacant_beds"] += 1
                continue

            dob = _parse_date(row["date_of_birth_raw"])
            patient_obj, patient_created = Patient.objects.update_or_create(
                medical_record_number=registro,
                defaults={"name": patient_name, "date_of_birth": dob},
            )
            if patient_created:
                stats["patients_created"] += 1
            else:
                stats["patients_updated"] += 1

            already_active = Hospitalization.objects.filter(
                bed=bed_obj, discharge_date__isnull=True
            ).exists()

            if not already_active:
                admission_dt = _parse_datetime(row["admission_hrro_raw"]) or timezone.now()
                exp_surg = _parse_date(row["expected_surgery_raw"])
                Hospitalization.objects.create(
                    patient=patient_obj,
                    bed=bed_obj,
                    admission_date=admission_dt,
                    procedure_planned=row["conduct"] or None,
                    current_status=row["conduct"] or None,
                    expected_surgery_date=exp_surg,
                    hipotese_diagnostica=row["diagnosis"] or None,
                    exames_pendentes=row["exams_pending"] or None,
                    necessidade_isolamento=(
                        "Precaução de Contato" if "PRECAUÇÃO" in cautela
                        else "Isolamento de Contato" if "ISOLAMENTO" in cautela
                        else None
                    ),
                )
                stats["hosp_created"] += 1

    return stats
