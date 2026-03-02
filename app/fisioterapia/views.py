from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from .models import FisioReport, FisioReportProcedure, FisioProcedure


BODY_PARTS = [
    ("membro_superior_esquerdo", "Membro Superior Esquerdo"),
    ("membro_superior_direito", "Membro Superior Direito"),
    ("membro_inferior_esquerdo", "Membro Inferior Esquerdo"),
    ("membro_inferior_direito", "Membro Inferior Direito"),
    ("coluna_cervical", "Coluna Cervical"),
    ("coluna_toracica", "Coluna Torácica"),
    ("coluna_lombar", "Coluna Lombar"),
    ("coluna_sacro", "Coluna Sacro"),
]


class FisioHomeView(LoginRequiredMixin, TemplateView):
    template_name = "fisioterapia/home.html"


class FisioCoordenadorView(LoginRequiredMixin, TemplateView):
    template_name = "fisioterapia/coordenador.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reports = FisioReport.objects.select_related("user").order_by("-created_at")

        context["reports"] = reports
        context["total_reports"] = reports.count()
        context["total_attendances"] = reports.aggregate(total=Sum("attendances"))["total"] or 0
        context["total_refusals"] = reports.aggregate(total=Sum("refusals"))["total"] or 0
        context["unique_users"] = reports.values("user_id").distinct().count()

        today = date.today()
        evolution = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_reports = reports.filter(report_date=d)
            evolution.append({
                "date": d.strftime("%d/%m"),
                "attendances": day_reports.aggregate(total=Sum("attendances"))["total"] or 0,
                "refusals": day_reports.aggregate(total=Sum("refusals"))["total"] or 0,
            })
        context["evolution_data"] = evolution

        body_part_data = (
            FisioReportProcedure.objects
            .values("body_part")
            .annotate(total=Sum("quantity"))
            .order_by("-total")
        )
        body_part_map = dict(BODY_PARTS)
        context["body_part_data"] = [
            {"name": body_part_map.get(item["body_part"], item["body_part"]), "value": item["total"] or 0}
            for item in body_part_data
        ]

        by_professional = (
            reports.values("user__first_name", "user__username")
            .annotate(attendances=Sum("attendances"), refusals=Sum("refusals"))
            .order_by("user__first_name", "user__username")
        )
        context["professional_data"] = [
            {
                "name": (item["user__first_name"] or item["user__username"] or "User").split(" ")[0],
                "attendances": item["attendances"] or 0,
                "refusals": item["refusals"] or 0,
            }
            for item in by_professional
        ]
        return context


class FisioAssistenciaView(LoginRequiredMixin, View):
    template_name = "fisioterapia/assistencia.html"

    def get(self, request):
        reports = FisioReport.objects.filter(user=request.user).order_by("-created_at")
        edit_id = request.GET.get("edit")
        edit_report = None
        edit_qty = {}
        edit_obs = {}
        if edit_id:
            edit_report = FisioReport.objects.filter(id=edit_id, user=request.user).first()
            if edit_report:
                items = FisioReportProcedure.objects.filter(report=edit_report)
                edit_qty = {item.body_part: item.quantity for item in items}
                edit_obs = {item.body_part: item.observation for item in items}
        body_parts = [
            {
                "key": key,
                "label": label,
                "qty": edit_qty.get(key) if edit_report else None,
                "obs": edit_obs.get(key) if edit_report else None,
            }
            for key, label in BODY_PARTS
        ]
        context = {
            "reports": reports,
            "body_parts": body_parts,
            "edit_report": edit_report,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        report_id = request.POST.get("report_id")
        report_date = request.POST.get("report_date")
        shift_type = request.POST.get("shift_type")
        refusals = request.POST.get("refusals") or "0"
        refusals_note = (request.POST.get("refusals_note") or "").strip()

        try:
            refusals_int = int(refusals)
        except ValueError:
            refusals_int = 0

        if not report_date or not shift_type:
            messages.error(request, "Preencha data e tipo de plantão.")
            return redirect("fisioterapia:assistencia")

        details = []
        attendances = 0
        for key, label in BODY_PARTS:
            qty_raw = request.POST.get(f"bp_{key}_qty") or "0"
            obs = (request.POST.get(f"bp_{key}_obs") or "").strip()
            try:
                qty = int(qty_raw)
            except ValueError:
                qty = 0
            if qty > 0 or obs:
                details.append({"key": key, "label": label, "qty": qty, "obs": obs})
            attendances += qty

        if attendances == 0:
            messages.error(request, "Informe ao menos um atendimento.")
            return redirect("fisioterapia:assistencia")

        if len(details) == 1:
            body_part_summary = details[0]["label"]
        else:
            body_part_summary = "Multiplas regioes"

        observations_parts = []
        for item in details:
            if item["obs"]:
                observations_parts.append(f"{item['label']}: {item['qty']} - {item['obs']}")
            else:
                observations_parts.append(f"{item['label']}: {item['qty']}")

        if refusals_int > 0 or refusals_note:
            if refusals_note:
                observations_parts.append(f"Recusas: {refusals_int} - {refusals_note}")
            else:
                observations_parts.append(f"Recusas: {refusals_int}")

        observations_summary = " | ".join(observations_parts) if observations_parts else None

        if report_id:
            report = get_object_or_404(FisioReport, id=report_id, user=request.user)
            report.report_date = report_date
            report.shift_type = shift_type
            report.attendances = attendances
            report.refusals = refusals_int
            report.refusals_note = refusals_note or None
            report.body_part = body_part_summary
            report.observations = observations_summary
            report.save()
            FisioReportProcedure.objects.filter(report=report).delete()
            action_msg = "Relatório atualizado com sucesso!"
        else:
            report = FisioReport.objects.create(
                user=request.user,
                report_date=report_date,
                shift_type=shift_type,
                attendances=attendances,
                refusals=refusals_int,
                refusals_note=refusals_note or None,
                body_part=body_part_summary,
                observations=observations_summary,
            )
            action_msg = "Relatório registrado com sucesso!"

        procedure, _ = FisioProcedure.objects.get_or_create(name="Atendimento")
        for item in details:
            if item["qty"] <= 0:
                continue
            FisioReportProcedure.objects.create(
                report=report,
                procedure=procedure,
                body_part=item["key"],
                quantity=item["qty"],
                observation=item["obs"] or None,
            )

        messages.success(request, action_msg)
        return redirect("fisioterapia:assistencia")


class FisioAssistenciaDeleteView(LoginRequiredMixin, View):
    def post(self, request, report_id):
        report = get_object_or_404(FisioReport, id=report_id, user=request.user)
        report.delete()
        messages.success(request, "Relatório removido.")
        return redirect("fisioterapia:assistencia")
