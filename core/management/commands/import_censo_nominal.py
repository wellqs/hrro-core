"""
import_censo_nominal
====================
Importa leitos, pacientes e internações a partir do CSV de Censo Nominal
no formato "KANBAN 2026 - CENSO_NOMINAL_*.csv".

O CSV é posicional (sem linha de cabeçalho utilizável):
  col 0  – Nº SUS / CPF (linha)
  col 1  – Nome da seção / clínica (apenas na 1ª linha de cada seção)
  col 2  – Identificador do leito  (ex.: "A 1 / 1", "B 13 / 39")
  col 3  – Data adm. hospital origem
  col 4  – Procedimento / origem
  col 5  – Data de entrada HRRO
  col 6  – Registro / prontuário
  col 7  – Nome do paciente
  col 8  – Sexo
  col 9  – Data de nascimento
  col 10 – Idade
  col 11 – Nº SUS / CPF
  col 12 – Hipótese diagnóstica
  col 13 – Conduta / status
  col 14 – CEREL
  col 15 – Previsão ortopédica / cirúrgica
  col 16 – Exames pendentes
  col 17 – Exames realizados
  col 18 – Cidade / UF
  col 19 – Especialidade
  col 25 – Infectado (SIM / blank)
  col 26 – Cautela (PADRÃO / PRECAUÇÃO / ISOLAMENTO …)

Uso:
  python manage.py import_censo_nominal \\
      --csv "data/KANBAN 2026 - CENSO_NOMINAL_15_04.csv" \\
      [--sync-hosp]   # encerra internações ativas antes de reimportar
      [--dry-run]     # apenas mostra o que seria feito
"""

import csv
import re
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Bed, Hospitalization, Patient

# Nomes de "paciente" que indicam leito vago / bloqueado / especial
VACANT_LABELS = {
    "VAGO", "VAGO-ISOLAMENTO", "ESTABILIZAÇÃO", "RESERVADO", "-", "",
    "TRIAGEM",
}

# Padrão de identificador de leito válido: "A 1 / 1", "B 13 / 39", "919.109 EXTRA" etc.
BED_ID_RE = re.compile(
    r"^([A-C]\s+\d+\s*/\s*\d+|[\d.]+\s+EXTRA)$", re.IGNORECASE
)

# Mapeamento de seção → categoria do leito
SECTION_CATEGORY = {
    "CLÍNICA A": ("CLÍNICA A", "NORMAL"),
    "EXTENSÃO": ("EXTENSÃO", "EXTENSAO"),
    "CLÍNICA A - INFECTADOS": ("CLÍNICA A - INFECTADOS", "INFECTADO"),
    "CLÍNICA B": ("CLÍNICA B", "NORMAL"),
    "CLÍNICA C": ("CLÍNICA C", "NORMAL"),
}

# Seções conhecidas que aparecem em col[1]
KNOWN_SECTIONS = set(SECTION_CATEGORY.keys())


def _clean(value: str) -> str:
    return (value or "").strip()


def _parse_date(raw: str):
    """Extrai a primeira data dd/mm/yyyy de um texto (pode ter quebras de linha)."""
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


class Command(BaseCommand):
    help = "Importa leitos, pacientes e internações a partir do CSV de Censo Nominal"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default="data/KANBAN 2026 - CENSO_NOMINAL_15_04.csv",
            help="Caminho do arquivo CSV.",
        )
        parser.add_argument(
            "--encoding",
            default="utf-8-sig",
            help="Encoding do CSV (default: utf-8-sig).",
        )
        parser.add_argument(
            "--sync-hosp",
            action="store_true",
            help="Encerra TODAS as internações ativas antes de importar (snapshot limpo).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas exibe o que seria importado, sem gravar no banco.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"Arquivo não encontrado: {csv_path}"))
            return

        dry_run = options["dry_run"]
        sync_hosp = options["sync_hosp"]

        current_clinic = "CLÍNICA A"
        current_category = "NORMAL"

        stats = {
            "beds_created": 0,
            "beds_updated": 0,
            "patients_created": 0,
            "patients_updated": 0,
            "hosp_created": 0,
            "hosp_closed": 0,
            "rows_skipped": 0,
            "vacant_beds": 0,
        }

        rows_to_process = []

        with csv_path.open("r", encoding=options["encoding"], newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                # Garante pelo menos 30 colunas
                while len(row) < 30:
                    row.append("")

                bed_id = _clean(row[2])
                if not BED_ID_RE.match(bed_id):
                    stats["rows_skipped"] += 1
                    continue

                # Atualiza seção atual se col[1] trouxer um nome de seção
                section_raw = _clean(row[1]).upper().replace("  ", " ")
                for known in KNOWN_SECTIONS:
                    if section_raw == known.upper():
                        current_clinic, current_category = SECTION_CATEGORY[known]
                        break

                rows_to_process.append({
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

        self.stdout.write(
            self.style.NOTICE(
                f"  {len(rows_to_process)} linhas de leito encontradas no CSV."
            )
        )

        if dry_run:
            self._dry_run_report(rows_to_process)
            return

        with transaction.atomic():
            if sync_hosp:
                closed = Hospitalization.objects.filter(
                    discharge_date__isnull=True
                ).update(discharge_date=timezone.now())
                stats["hosp_closed"] = closed
                self.stdout.write(
                    self.style.WARNING(f"  {closed} internações ativas encerradas (--sync-hosp).")
                )

            for row in rows_to_process:
                bed_id = row["bed_id"]

                # --- Categoria refinada por infectado/cautela ---
                category = row["category"]
                cautela = row["cautela"].upper()
                if row["infected"] or "ISOLAMENTO" in cautela or "PRECAUÇÃO" in cautela:
                    category = "INFECTADO"
                if "EXTRA" in bed_id.upper():
                    category = "EXTRA"
                if "EXTENSÃO" in row["clinic"].upper():
                    category = "EXTENSAO"

                # --- Leito ---
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

                # --- Leito vago / bloqueado → para aqui ---
                patient_name = row["patient_name"]
                registro = row["registro"]
                name_upper = patient_name.upper()
                if name_upper in VACANT_LABELS or not registro:
                    stats["vacant_beds"] += 1
                    continue

                # --- Paciente ---
                dob = _parse_date(row["date_of_birth_raw"])
                patient_obj, patient_created = Patient.objects.update_or_create(
                    medical_record_number=registro,
                    defaults={
                        "name": patient_name,
                        "date_of_birth": dob,
                    },
                )
                if patient_created:
                    stats["patients_created"] += 1
                else:
                    stats["patients_updated"] += 1

                # --- Internação (só cria se não houver ativa para este leito) ---
                admission_dt = _parse_datetime(row["admission_hrro_raw"]) or timezone.now()
                exp_surg = _parse_date(row["expected_surgery_raw"])

                already_active = Hospitalization.objects.filter(
                    bed=bed_obj,
                    discharge_date__isnull=True,
                ).exists()

                if not already_active:
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
                            "Precaução de Contato"
                            if "PRECAUÇÃO" in cautela
                            else "Isolamento de Contato"
                            if "ISOLAMENTO" in cautela
                            else None
                        ),
                    )
                    stats["hosp_created"] += 1

        self._print_summary(stats)

    def _dry_run_report(self, rows):
        self.stdout.write(self.style.WARNING("\n[DRY-RUN] Resumo do que seria importado:\n"))
        occupied = [r for r in rows if r["patient_name"].upper() not in VACANT_LABELS and r["registro"]]
        vacant = [r for r in rows if r["patient_name"].upper() in VACANT_LABELS or not r["registro"]]
        self.stdout.write(f"  Leitos ocupados : {len(occupied)}")
        self.stdout.write(f"  Leitos vagos    : {len(vacant)}")
        self.stdout.write(f"  Total de leitos : {len(rows)}")
        clinics = {}
        for r in rows:
            clinics.setdefault(r["clinic"], {"total": 0, "ocupados": 0})
            clinics[r["clinic"]]["total"] += 1
            if r["patient_name"].upper() not in VACANT_LABELS and r["registro"]:
                clinics[r["clinic"]]["ocupados"] += 1
        self.stdout.write("\n  Por clínica:")
        for clinic, data in clinics.items():
            self.stdout.write(
                f"    {clinic:<35} {data['ocupados']:>3}/{data['total']:>3} ocupados"
            )

    def _print_summary(self, stats):
        self.stdout.write(self.style.SUCCESS("\n✔ Importação concluída:"))
        self.stdout.write(f"  Leitos  criados   : {stats['beds_created']}")
        self.stdout.write(f"  Leitos  atualizados: {stats['beds_updated']}")
        self.stdout.write(f"  Leitos  vagos      : {stats['vacant_beds']}")
        self.stdout.write(f"  Pacientes criados  : {stats['patients_created']}")
        self.stdout.write(f"  Pacientes atualizados: {stats['patients_updated']}")
        self.stdout.write(f"  Internações criadas: {stats['hosp_created']}")
        if stats["hosp_closed"]:
            self.stdout.write(
                self.style.WARNING(f"  Internações encerradas (sync): {stats['hosp_closed']}")
            )
