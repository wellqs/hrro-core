"""
import_censo_sheets
====================
Importa leitos, pacientes e internações diretamente da planilha Google
Sheets do Censo Nominal (sem precisar baixar/subir CSV manualmente).

Uso:
  python manage.py import_censo_sheets [--sync-hosp] [--dry-run]

Pensado para rodar via agendador (Agendador de Tarefas do Windows / cron)
uma vez por dia.
"""

from django.core.management.base import BaseCommand, CommandError

from core.censo_import import VACANT_LABELS, import_censo, parse_censo_rows
from core.censo_sheets import fetch_censo_rows


class Command(BaseCommand):
    help = "Importa leitos, pacientes e internações a partir da planilha Google Sheets do Censo Nominal"

    def add_arguments(self, parser):
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
        try:
            raw_rows = fetch_censo_rows()
        except Exception as e:
            raise CommandError(f"Erro ao buscar a planilha Google Sheets: {e}")

        rows = parse_censo_rows(raw_rows)
        self.stdout.write(self.style.NOTICE(f"  {len(rows)} linhas de leito encontradas na planilha."))

        if not rows:
            self.stdout.write(self.style.WARNING("Nenhum leito encontrado. Verifique a aba/planilha configurada."))
            return

        if options["dry_run"]:
            occupied = [r for r in rows if r["patient_name"].upper() not in VACANT_LABELS and r["registro"]]
            vacant = [r for r in rows if r["patient_name"].upper() in VACANT_LABELS or not r["registro"]]
            self.stdout.write(self.style.WARNING("\n[DRY-RUN] Resumo do que seria importado:\n"))
            self.stdout.write(f"  Leitos ocupados : {len(occupied)}")
            self.stdout.write(f"  Leitos vagos    : {len(vacant)}")
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
