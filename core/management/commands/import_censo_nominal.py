"""
import_censo_nominal
====================
Importa leitos, pacientes e internações a partir do CSV de Censo Nominal
no formato "KANBAN 2026 - CENSO_NOMINAL_*.csv".

Uso:
  python manage.py import_censo_nominal \\
      --csv "data/KANBAN 2026 - CENSO_NOMINAL_15_04.csv" \\
      [--sync-hosp]
      [--dry-run]
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from core.censo_import import VACANT_LABELS, import_censo, parse_censo_csv


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
            help="Encerra TODAS as internações ativas antes de importar.",
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

        with csv_path.open("rb") as f:
            rows = parse_censo_csv(f, encoding=options["encoding"])

        self.stdout.write(self.style.NOTICE(f"  {len(rows)} linhas de leito encontradas no CSV."))

        if options["dry_run"]:
            occupied = [r for r in rows if r["patient_name"].upper() not in VACANT_LABELS and r["registro"]]
            vacant = [r for r in rows if r["patient_name"].upper() in VACANT_LABELS or not r["registro"]]
            self.stdout.write(self.style.WARNING("\n[DRY-RUN] Resumo do que seria importado:\n"))
            self.stdout.write(f"  Leitos ocupados : {len(occupied)}")
            self.stdout.write(f"  Leitos vagos    : {len(vacant)}")
            clinics = {}
            for r in rows:
                clinics.setdefault(r["clinic"], {"total": 0, "ocupados": 0})
                clinics[r["clinic"]]["total"] += 1
                if r["patient_name"].upper() not in VACANT_LABELS and r["registro"]:
                    clinics[r["clinic"]]["ocupados"] += 1
            self.stdout.write("\n  Por clínica:")
            for clinic, data in clinics.items():
                self.stdout.write(f"    {clinic:<35} {data['ocupados']:>3}/{data['total']:>3} ocupados")
            return

        stats = import_censo(rows, sync_hosp=options["sync_hosp"])

        self.stdout.write(self.style.SUCCESS("\n✔ Importação concluída:"))
        self.stdout.write(f"  Leitos criados      : {stats['beds_created']}")
        self.stdout.write(f"  Leitos atualizados  : {stats['beds_updated']}")
        self.stdout.write(f"  Leitos vagos        : {stats['vacant_beds']}")
        self.stdout.write(f"  Pacientes criados   : {stats['patients_created']}")
        self.stdout.write(f"  Pacientes atualizados: {stats['patients_updated']}")
        self.stdout.write(f"  Internações criadas : {stats['hosp_created']}")
        if stats["hosp_closed"]:
            self.stdout.write(self.style.WARNING(f"  Internações encerradas (sync): {stats['hosp_closed']}"))
