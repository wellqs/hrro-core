import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from core.models import Bed


class Command(BaseCommand):
    help = "Popula leitos a partir do arquivo ocupacao.csv"

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
            help="Remove todos os leitos antes de importar.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"Arquivo nao encontrado: {csv_path}"))
            return

        if options["clear"]:
            Bed.objects.all().delete()
            self.stdout.write(self.style.WARNING("Leitos removidos antes da importacao."))

        def normalize_fieldnames(fieldnames):
            normalized = []
            for index, field in enumerate(fieldnames or []):
                key = (field or "").strip()
                normalized.append(key or f"__blank_{index}")
            return normalized

        def infer_clinic(identifier):
            prefix = (identifier or "").strip().upper()[:1]
            if prefix == "A":
                return "CLÍNICA A"
            if prefix == "B":
                return "CLÍNICA B"
            if prefix == "C":
                return "CLÍNICA C"
            return "EXTRA"

        created = 0
        updated = 0
        skipped = 0
        with csv_path.open("r", encoding=options["encoding"], newline="") as f:
            reader = csv.DictReader(f, delimiter=options["delimiter"])
            reader.fieldnames = normalize_fieldnames(reader.fieldnames)
            if "LEITO" not in reader.fieldnames:
                self.stderr.write(self.style.ERROR("CSV nao possui coluna 'LEITO'."))
                return

            for row in reader:
                bed_raw = (row.get("LEITO") or "").strip()
                if not bed_raw:
                    skipped += 1
                    continue

                clinic = infer_clinic(bed_raw)
                identifier = bed_raw

                obj, was_created = Bed.objects.update_or_create(
                    identifier=identifier,
                    defaults={
                        "clinic": clinic,
                        "category": "NORMAL",
                        "is_active": True,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Importacao concluida. Criados: {created}, Atualizados: {updated}, Ignorados: {skipped}"
        ))
