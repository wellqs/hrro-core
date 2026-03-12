from django.db import models
from django.contrib.auth.models import User


class FisioProcedure(models.Model):
    name = models.CharField(max_length=120, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Procedimento (Fisio)"
        verbose_name_plural = "Procedimentos (Fisio)"
        ordering = ["name"]

    def __str__(self):
        return self.name


class FisioReport(models.Model):
    SHIFT_CHOICES = [
        ("h6", "6h"),
        ("h12", "12h"),
    ]

    BODY_PART_CHOICES = [
        ("membro_superior_esquerdo", "Membro Superior Esquerdo"),
        ("membro_superior_direito", "Membro Superior Direito"),
        ("membro_inferior_esquerdo", "Membro Inferior Esquerdo"),
        ("membro_inferior_direito", "Membro Inferior Direito"),
        ("coluna_cervical", "Coluna Cervical"),
        ("coluna_toracica", "Coluna Torácica"),
        ("coluna_lombar", "Coluna Lombar"),
        ("coluna_sacro", "Coluna Sacro"),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="fisio_reports")
    report_date = models.DateField()
    shift_type = models.CharField(max_length=3, choices=SHIFT_CHOICES)
    attendances = models.PositiveIntegerField()
    refusals = models.PositiveIntegerField(default=0)
    refusals_note = models.TextField(blank=True, null=True)
    body_part = models.CharField(max_length=80)
    observations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Relatório Fisio"
        verbose_name_plural = "Relatórios Fisio"
        ordering = ["-report_date", "-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.report_date}"


class FisioReportProcedure(models.Model):
    BODY_PART_CHOICES = FisioReport.BODY_PART_CHOICES

    report = models.ForeignKey(FisioReport, on_delete=models.CASCADE, related_name="procedures")
    procedure = models.ForeignKey(FisioProcedure, on_delete=models.PROTECT, related_name="report_items")
    body_part = models.CharField(max_length=80, choices=BODY_PART_CHOICES)
    quantity = models.PositiveIntegerField()
    observation = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Detalhe do Relatório (Fisio)"
        verbose_name_plural = "Detalhes do Relatório (Fisio)"
        indexes = [
            models.Index(fields=["report"]),
            models.Index(fields=["procedure"]),
        ]

    def __str__(self):
        return f"{self.report_id} - {self.body_part} ({self.quantity})"


class FisioUserAudit(models.Model):
    ACTION_CHOICES = [
        ("deactivated", "Desativado"),
        ("reactivated", "Reativado"),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="fisio_audits")
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="fisio_audit_actions")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Auditoria de Usuário (Fisio)"
        verbose_name_plural = "Auditorias de Usuário (Fisio)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} ({self.created_at:%d/%m/%Y})"
