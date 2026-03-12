from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.db.models import Max, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView

from .models import FisioReport, FisioReportProcedure, FisioProcedure, FisioUserAudit

try:
    from weasyprint import HTML
except Exception:
    HTML = None


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

FISIO_COORD_GROUP = "Fisioterapia Coordenador"
FISIO_ASSIST_GROUP = "Fisioterapia Assistencial"


class FisioHomeView(LoginRequiredMixin, TemplateView):
    template_name = "fisioterapia/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["user_display"] = user.first_name or user.username
        return context


class FisioCoordenadorView(LoginRequiredMixin, TemplateView):
    template_name = "fisioterapia/coordenador.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        return super().dispatch(request, *args, **kwargs)

    def _get_users(self):
        coord_group, _ = Group.objects.get_or_create(name=FISIO_COORD_GROUP)
        assist_group, _ = Group.objects.get_or_create(name=FISIO_ASSIST_GROUP)
        return (
            User.objects.filter(groups__in=[coord_group, assist_group])
            .distinct()
            .order_by("-is_active", "first_name", "username")
        )

    def _get_filtered_reports(self):
        reports = FisioReport.objects.select_related("user").order_by("-report_date", "-created_at")
        user_id = self.request.GET.get("user_id")
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        if user_id:
            reports = reports.filter(user_id=user_id)
        if date_from:
            try:
                reports = reports.filter(report_date__gte=date_from)
            except ValueError:
                pass
        if date_to:
            try:
                reports = reports.filter(report_date__lte=date_to)
            except ValueError:
                pass
        return reports

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reports = self._get_filtered_reports()

        context["reports"] = reports
        context["total_reports"] = reports.count()
        context["total_attendances"] = reports.aggregate(total=Sum("attendances"))["total"] or 0
        context["total_refusals"] = reports.aggregate(total=Sum("refusals"))["total"] or 0
        context["unique_users"] = reports.values("user_id").distinct().count()
        context["users_filter"] = self._get_users()
        context["filter_user_id"] = self.request.GET.get("user_id") or ""
        context["filter_date_from"] = self.request.GET.get("date_from") or ""
        context["filter_date_to"] = self.request.GET.get("date_to") or ""

        max_date = reports.aggregate(max_date=Max("report_date"))["max_date"]
        today = max_date or date.today()
        range_raw = self.request.GET.get("range")
        try:
            range_days = int(range_raw) if range_raw else 7
        except ValueError:
            range_days = 7
        if range_days not in (7, 30, 60, 90):
            range_days = 7
        context["range_days"] = range_days

        evolution = []
        for i in range(range_days - 1, -1, -1):
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


class FisioEquipeView(LoginRequiredMixin, View):
    template_name = "fisioterapia/equipe.html"

    def get(self, request):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        coord_group, _ = Group.objects.get_or_create(name=FISIO_COORD_GROUP)
        assist_group, _ = Group.objects.get_or_create(name=FISIO_ASSIST_GROUP)
        users = User.objects.filter(groups__in=[coord_group, assist_group]).distinct().order_by("-is_active", "first_name", "username")
        edit_user = None
        edit_role = None
        edit_id = request.GET.get("edit")
        if edit_id:
            edit_user = users.filter(id=edit_id).first()
            if edit_user:
                if edit_user.groups.filter(name=FISIO_COORD_GROUP).exists():
                    edit_role = "coordenador"
                elif edit_user.groups.filter(name=FISIO_ASSIST_GROUP).exists():
                    edit_role = "assistencial"
        return render(request, self.template_name, {
            "users": users,
            "edit_user": edit_user,
            "edit_role": edit_role,
        })

    def post(self, request):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        role = request.POST.get("role")
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = (request.POST.get("password") or "").strip()
        user_id = request.POST.get("user_id")

        coord_group, _ = Group.objects.get_or_create(name=FISIO_COORD_GROUP)
        assist_group, _ = Group.objects.get_or_create(name=FISIO_ASSIST_GROUP)

        if user_id:
            user = get_object_or_404(User, id=user_id)
            if not username:
                messages.error(request, "Informe o usuário.")
                return redirect("fisioterapia:equipe")
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                messages.error(request, "Este usuário já existe.")
                return redirect("fisioterapia:equipe")
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.email = email or None
            if password:
                user.set_password(password)
            user.save()
            user.groups.remove(coord_group, assist_group)
            if role == "coordenador":
                user.groups.add(coord_group)
            else:
                user.groups.add(assist_group)
            messages.success(request, "Usuário atualizado com sucesso.")
            return redirect("fisioterapia:equipe")

        if not username or not password:
            messages.error(request, "Informe usuário e senha.")
            return redirect("fisioterapia:equipe")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Este usuário já existe.")
            return redirect("fisioterapia:equipe")

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email or None,
            first_name=first_name,
            last_name=last_name,
        )

        if role == "coordenador":
            user.groups.add(coord_group)
        else:
            user.groups.add(assist_group)

        messages.success(request, "Usuário cadastrado com sucesso.")
        return redirect("fisioterapia:equipe")


class FisioEquipeDeactivateView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            messages.error(request, "Você não pode desativar o seu próprio usuário.")
            return redirect("fisioterapia:equipe")
        if user.is_superuser and not request.user.is_superuser:
            messages.error(request, "Apenas um superusuário pode desativar outro superusuário.")
            return redirect("fisioterapia:equipe")
        if not user.is_active:
            messages.info(request, "Usuário já está inativo.")
            return redirect("fisioterapia:equipe")
        user.is_active = False
        user.save(update_fields=["is_active"])
        FisioUserAudit.objects.create(
            user=user,
            action="deactivated",
            performed_by=request.user,
        )
        messages.success(request, "Usuário desativado com sucesso.")
        return redirect("fisioterapia:equipe")


class FisioEquipeReactivateView(LoginRequiredMixin, View):
    def post(self, request, user_id):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        user = get_object_or_404(User, id=user_id)
        if user.is_active:
            messages.info(request, "Usuário já está ativo.")
            return redirect("fisioterapia:equipe")
        user.is_active = True
        user.save(update_fields=["is_active"])
        FisioUserAudit.objects.create(
            user=user,
            action="reactivated",
            performed_by=request.user,
        )
        messages.success(request, "Usuário reativado com sucesso.")
        return redirect("fisioterapia:equipe")


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
        if not request.user.is_active:
            messages.error(request, "Seu usuário está inativo.")
            return redirect("fisioterapia:assistencia")
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

        duplicate_qs = FisioReport.objects.filter(
            user=request.user,
            report_date=report_date,
            shift_type=shift_type,
        )
        if report_id:
            duplicate_qs = duplicate_qs.exclude(id=report_id)
        if duplicate_qs.exists():
            messages.error(request, "Já existe relatório para este profissional, data e plantão.")
            return redirect("fisioterapia:assistencia")

        if len(details) == 1:
            body_part_summary = details[0]["label"]
        else:
            body_part_summary = "Múltiplas regiões"

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


class FisioCoordinatorReportView(LoginRequiredMixin, View):
    template_name = "fisioterapia/relatorio_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        return super().dispatch(request, *args, **kwargs)

    def _get_users(self):
        coord_group, _ = Group.objects.get_or_create(name=FISIO_COORD_GROUP)
        assist_group, _ = Group.objects.get_or_create(name=FISIO_ASSIST_GROUP)
        return (
            User.objects.filter(groups__in=[coord_group, assist_group])
            .distinct()
            .order_by("-is_active", "first_name", "username")
        )

    def get(self, request, report_id=None):
        report = None
        edit_qty = {}
        edit_obs = {}
        selected_user_id = request.GET.get("user_id")
        if report_id:
            report = get_object_or_404(FisioReport, id=report_id)
            selected_user_id = str(report.user_id)
            items = FisioReportProcedure.objects.filter(report=report)
            edit_qty = {item.body_part: item.quantity for item in items}
            edit_obs = {item.body_part: item.observation for item in items}

        body_parts = [
            {
                "key": key,
                "label": label,
                "qty": edit_qty.get(key) if report else None,
                "obs": edit_obs.get(key) if report else None,
            }
            for key, label in BODY_PARTS
        ]
        context = {
            "report": report,
            "body_parts": body_parts,
            "users": self._get_users(),
            "selected_user_id": selected_user_id,
        }
        return render(request, self.template_name, context)

    def post(self, request, report_id=None):
        user_id = request.POST.get("user_id")
        report_date = request.POST.get("report_date")
        shift_type = request.POST.get("shift_type")
        refusals = request.POST.get("refusals") or "0"
        refusals_note = (request.POST.get("refusals_note") or "").strip()

        if not user_id:
            messages.error(request, "Selecione o profissional.")
            return redirect(request.path)

        try:
            refusals_int = int(refusals)
        except ValueError:
            refusals_int = 0

        if not report_date or not shift_type:
            messages.error(request, "Preencha data e tipo de plantão.")
            return redirect(request.path)

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
            return redirect(request.path)

        if len(details) == 1:
            body_part_summary = details[0]["label"]
        else:
            body_part_summary = "Múltiplas regiões"

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

        user = get_object_or_404(User, id=user_id)
        if not report_id and not user.is_active:
            messages.error(request, "Não é possível registrar relatório para usuário inativo.")
            return redirect(request.path)

        duplicate_qs = FisioReport.objects.filter(
            user=user,
            report_date=report_date,
            shift_type=shift_type,
        )
        if report_id:
            duplicate_qs = duplicate_qs.exclude(id=report_id)
        if duplicate_qs.exists():
            messages.error(request, "Já existe relatório para este profissional, data e plantão.")
            return redirect(request.path)

        if report_id:
            report = get_object_or_404(FisioReport, id=report_id)
            report.user = user
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
                user=user,
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
        return redirect("fisioterapia:coordenador")


class FisioCoordinatorReportDetailView(LoginRequiredMixin, View):
    template_name = "fisioterapia/relatorio_detail.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, report_id):
        report = get_object_or_404(
            FisioReport.objects.select_related("user").prefetch_related("procedures"),
            id=report_id,
        )
        procedures = report.procedures.all()
        return render(request, self.template_name, {
            "report": report,
            "procedures": procedures,
        })


class FisioCoordinatorReportDeleteView(LoginRequiredMixin, View):
    def post(self, request, report_id):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        report = get_object_or_404(FisioReport, id=report_id)
        report.delete()
        messages.success(request, "Relatório removido com sucesso.")
        return redirect("fisioterapia:coordenador")


class FisioCoordinatorReportPDFView(LoginRequiredMixin, View):
    def get(self, request, report_id):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        if HTML is None:
            return HttpResponse("Dependência do WeasyPrint ausente no ambiente.", status=500)

        report = get_object_or_404(
            FisioReport.objects.select_related("user").prefetch_related("procedures"),
            id=report_id,
        )
        procedures = report.procedures.all()

        context = {
            "report": report,
            "procedures": procedures,
        }
        html_string = render_to_string("fisioterapia/relatorio_pdf.html", context)
        base_url = request.build_absolute_uri("/")
        pdf = HTML(string=html_string, base_url=base_url).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="relatorio_fisio_{report.id}.pdf"'
        return response


class FisioCoordinatorReportsPDFView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.is_superuser and not request.user.groups.filter(name=FISIO_COORD_GROUP).exists():
            messages.error(request, "Você não tem permissão para acessar esta área.")
            return redirect("fisioterapia:home")
        if HTML is None:
            return HttpResponse("Dependência do WeasyPrint ausente no ambiente.", status=500)

        reports = FisioReport.objects.select_related("user").order_by("-report_date", "-created_at")
        user_id = request.GET.get("user_id")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        if user_id:
            reports = reports.filter(user_id=user_id)
        if date_from:
            reports = reports.filter(report_date__gte=date_from)
        if date_to:
            reports = reports.filter(report_date__lte=date_to)

        context = {
            "reports": reports,
            "generated_at": date.today(),
        }
        html_string = render_to_string("fisioterapia/relatorios_pdf.html", context)
        base_url = request.build_absolute_uri("/")
        pdf = HTML(string=html_string, base_url=base_url).write_pdf()
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="relatorios_fisio.pdf"'
        return response
