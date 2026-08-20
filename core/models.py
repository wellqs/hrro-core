from django.db import models
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.utils import timezone

# Modelo Principal - Cirurgia
class Surgery(models.Model):
    # ... (código existente da classe Surgery) ...
    STATUS_CHOICES = [('AGENDADA', 'Agendada'), ('REALIZADA', 'Realizada'), ('CANCELADA', 'Cancelada')]
    MOTIVO_PACIENTE_CHOICES = [('MEDICACAO', 'Medicação'), ('QUEBRA_JEJUM', 'Quebra de jejum'), ('EXAMES_ALTERADOS', 'Exames alterados')]
    MOTIVO_INSTITUCIONAL_CHOICES = [('FALTA_INSUMOS', 'Falta de insumos'), ('FALTA_EQUIPAMENTO', 'Falta de equipamento'), ('EQUIPAMENTO_DEFEITO', 'Equipamento com defeito'), ('INDISPONIBILIDADE_PROFISSIONAL', 'Indisponibilidade de profissional')]
    SETOR_CANCELAMENTO_CHOICES = [('NIR', 'NIR (Regulação)'), ('GENF', 'GENF (Enfermagem)'), ('CC', 'CC (Centro Cirúrgico)'), ('OUTRO', 'Outro')]
    patient_name = models.CharField(max_length=200, verbose_name="Nome do Paciente")
    procedure_name = models.CharField(max_length=200, verbose_name="Nome do Procedimento")
    scheduled_date = models.DateTimeField(verbose_name="Data Agendada")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='AGENDADA')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    created_at = models.DateTimeField(auto_now_add=True)
    motivo_paciente = models.CharField(max_length=50, choices=MOTIVO_PACIENTE_CHOICES, blank=True, null=True, verbose_name="Motivo do Paciente")
    motivo_institucional = models.CharField(max_length=50, choices=MOTIVO_INSTITUCIONAL_CHOICES, blank=True, null=True, verbose_name="Motivo Institucional")
    observacoes_cancelamento = models.CharField(max_length=150, blank=True, null=True, verbose_name="Observações do Cancelamento")
    setor_cancelamento = models.CharField(max_length=10, choices=SETOR_CANCELAMENTO_CHOICES, blank=True, null=True, verbose_name="Setor Responsável pelo Cancelamento")
    class Meta: verbose_name = "Cirurgia"; verbose_name_plural = "Cirurgias"; ordering = ['-scheduled_date']
    def __str__(self): return f"{self.procedure_name} - {self.patient_name}"
    def get_absolute_url(self): return reverse('surgery_detail', kwargs={'pk': self.pk})

# --- MODELO CENTRAL DE PACIENTES ---
class Patient(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nome Completo")
    date_of_birth = models.DateField(verbose_name="Data de Nascimento", null=True, blank=True)
    medical_record_number = models.CharField(max_length=50, unique=True, verbose_name="Número do Prontuário")
    # TODO: Adicionar campos CNS, Nome Social, Sexo, Alergia a Látex aqui depois
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_patients', verbose_name="Cadastrado por")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    class Meta: verbose_name = "Paciente"; verbose_name_plural = "Pacientes"; ordering = ['name']
    def __str__(self): return f"{self.name} ({self.medical_record_number})"
    def get_absolute_url(self): return reverse('patient_detail', kwargs={'pk': self.pk}) # Assumindo que teremos essa URL

# --- MODELOS PARA GERENCIAMENTO DE LEITOS (NIR) ---
class Bed(models.Model):
    CATEGORY_CHOICES = [('NORMAL', 'Normal'), ('INFECTADO', 'Infectado'), ('EXTENSAO', 'Extensão'), ('EXTRA', 'Extra')]
    identifier = models.CharField(max_length=50, unique=True, verbose_name="Identificador do Leito")
    clinic = models.CharField(max_length=100, verbose_name="Clínica")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='NORMAL', verbose_name="Categoria")
    is_active = models.BooleanField(default=True, verbose_name="Leito Ativo?")
    class Meta: verbose_name = "Leito"; verbose_name_plural = "Leitos"; ordering = ['clinic', 'identifier']
    def __str__(self): return self.identifier

class Hospitalization(models.Model):
    # --- CAMPOS EXISTENTES ---
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='hospitalizations', verbose_name="Paciente")
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='hospitalizations', verbose_name="Leito")
    admission_date = models.DateTimeField(verbose_name="Data/Hora de Admissão")
    discharge_date = models.DateTimeField(verbose_name="Data/Hora de Saída", null=True, blank=True)
    procedure_planned = models.CharField(max_length=255, blank=True, null=True, verbose_name="Procedimento Previsto")
    current_status = models.CharField(max_length=100, blank=True, null=True, verbose_name="Status Atual") # Mapeado de 'STATUS CIRURGICO'
    expected_surgery_date = models.DateField(null=True, blank=True, verbose_name="Previsão Cirúrgica") # Mapeado de 'PREVISÃO DE ALTA/CIRURGIA'
    notes = models.TextField(blank=True, null=True, verbose_name="Observações") # Mapeado de 'OBSERVAÇÃO GERAL' + 'OBSERVAÇÃO NIR'

    # --- NOVOS CAMPOS ADICIONADOS BASEADO NO CSV/SCRIPT ---
    numero_atendimento = models.CharField(max_length=50, blank=True, null=True, verbose_name="Nº do Atendimento") # De 'Nº DO AT'
    hipotese_diagnostica = models.TextField(blank=True, null=True, verbose_name="Hipótese Diagnóstica") # De 'HIPÓTESE DIAGNÓSTICA'
    convenio = models.CharField(max_length=100, blank=True, null=True, verbose_name="Convênio") # De 'CONVÊNIO'
    exames_pendentes = models.TextField(blank=True, null=True, verbose_name="Exames Pendentes") # De 'EXAMES PENDENTES'
    parecer_especialidade = models.TextField(blank=True, null=True, verbose_name="Parecer de Especialidade") # De 'PARECER DE ESPECIALIDADE'
    avaliacao_nurse_nutri = models.TextField(blank=True, null=True, verbose_name="Avaliação Nurse/Nutri") # De 'AVALIAÇÃO NURSE/NUTRI'
    necessidade_isolamento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Necessidade de Isolamento") # De 'NECESSIDADE DE ISOLAMENTO'
    precaucoes_especificas = models.TextField(blank=True, null=True, verbose_name="Precauções Específicas") # De 'PRECAUÇÕES ESPECÍFICAS'
    risco_cirurgico_alto = models.BooleanField(null=True, blank=True, verbose_name="Risco Cirúrgico Alto") # De 'RISCO CIRÚRGICO ALTO'
    nome_cirurgiao = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nome Cirurgião") # De 'NOME CIRURGIÃO'
    opme_necessario = models.BooleanField(null=True, blank=True, verbose_name="OPME Necessário") # De 'OPME NECESSÁRIO'
    avaliacao_social = models.TextField(blank=True, null=True, verbose_name="Avaliação Social") # De 'AVALIAÇÃO SOCIAL'
    internacao_prolongada = models.BooleanField(null=True, blank=True, verbose_name="Internação Prolongada") # De 'INTERNAÇÃO PROLONGADA'
    # --------------------------------------------------------

    # Auditoria
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_hospitalizations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta: verbose_name = "Internação/Ocupação"; verbose_name_plural = "Internações/Ocupações"; ordering = ['-admission_date']
    def __str__(self):
        status = "Ativa" if self.discharge_date is None else "Encerrada"
        return f"Internação {status} de {self.patient.name} no leito {self.bed.identifier}"

# --- FIM DOS MODELOS NIR ---

# Modelos Setoriais (Cirurgia)
# ... (RegulationData, SurgicalData, BillingData, CMEData, OPMEData, NursingChecklist) ...
class RegulationData(models.Model):
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, primary_key=True, verbose_name="Cirurgia")
    entry_date = models.DateField(verbose_name="Data de Entrada na Regulação", null=True, blank=True)
    is_approved = models.BooleanField(default=False, verbose_name="Aprovado?")
    notes = models.TextField(blank=True, null=True, verbose_name="Observações")
    def __str__(self): return f"Dados de Regulação para {self.surgery.patient_name}"

class SurgicalData(models.Model):
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, primary_key=True, verbose_name="Cirurgia")
    start_time = models.DateTimeField(verbose_name="Início da Cirurgia", null=True, blank=True)
    end_time = models.DateTimeField(verbose_name="Fim da Cirurgia", null=True, blank=True)
    room = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sala Cirúrgica")
    surgeon = models.CharField(max_length=200, blank=True, null=True, verbose_name="Cirurgião") # CUIDADO: Redundante com Hospitalization.nome_cirurgiao?
    checklist_cirurgia_segura = models.BooleanField(default=False, verbose_name="Checklist de Cirurgia Segura Realizado?")
    def __str__(self): return f"Dados do Centro Cirúrgico para {self.surgery.patient_name}"

class BillingData(models.Model):
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, primary_key=True, verbose_name="Cirurgia")
    invoice_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="Código da Fatura")
    is_billed = models.BooleanField(default=False, verbose_name="Faturado?")
    def __str__(self): return f"Dados de Faturamento para {self.surgery.patient_name}"

class CMEData(models.Model):
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, primary_key=True, verbose_name="Cirurgia")
    material_sterilized = models.BooleanField(default=False, verbose_name="Material Esterilizado?")
    sterilization_date = models.DateTimeField(null=True, blank=True, verbose_name="Data da Esterilização")
    notes = models.TextField(blank=True, null=True, verbose_name="Observações da CME")
    def __str__(self): return f"Dados da CME para {self.surgery.patient_name}"

class OPMEData(models.Model):
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, primary_key=True, verbose_name="Cirurgia")
    materials_list = models.TextField(verbose_name="Lista de Materiais OPME", blank=True, null=True)
    is_authorized = models.BooleanField(default=False, verbose_name="Autorizado?")
    supplier = models.CharField(max_length=200, blank=True, null=True, verbose_name="Fornecedor")
    def __str__(self): return f"Dados de OPME para {self.surgery.patient_name}"

class NursingChecklist(models.Model):
    surgery = models.OneToOneField(Surgery, on_delete=models.CASCADE, primary_key=True, verbose_name="Cirurgia")
    patient_fasting = models.BooleanField(default=False, verbose_name="Paciente em Jejum?")
    consent_form_signed = models.BooleanField(default=False, verbose_name="Termo de Consentimento Assinado?")
    pre_op_medication_given = models.BooleanField(default=False, verbose_name="Medicação Pré-operatória Administrada?")
    notes = models.TextField(blank=True, null=True, verbose_name="Observações de Enfermagem")
    def __str__(self): return f"Checklist de Enfermagem para {self.surgery.patient_name}"

# Modelos Indicadores NSP
# ... (Sector, Indicator, IndicatorData) ...
class Sector(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome do Setor")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição")
    group = models.OneToOneField(Group, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Grupo de Permissão")
    class Meta: verbose_name = "Setor"; verbose_name_plural = "Setores"; ordering = ['name']
    def __str__(self): return self.name


# Cores por tipo de setor no organograma institucional (paleta HRRO)
ORG_TIPO_COLORS = {
    'direcao': '#0d1b3e',
    'diretoria': '#0284c7',
    'gerencia': '#4338ca',
    'nucleo': '#059669',
    'assistencial': '#9d174d',
    'administrativo': '#475569',
    'unidade': '#b91c1c',
    'comissao': '#b45309',
}

# Organograma institucional (hierarquia real de setores do hospital)
class OrgUnit(models.Model):
    TIPO_CHOICES = [
        ('direcao', 'Direção'),
        ('diretoria', 'Diretoria'),
        ('gerencia', 'Gerência'),
        ('nucleo', 'Núcleo'),
        ('assistencial', 'Assistencial'),
        ('administrativo', 'Administrativo'),
        ('unidade', 'Unidade'),
        ('comissao', 'Comissão'),
    ]
    NIVEL_CHOICES = [
        (0, 'Direção Máxima'),
        (1, 'Diretorias e Adjuntos'),
        (2, 'Gerências, Núcleos e Centrais'),
        (3, 'Unidades Especializadas'),
    ]
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nome = models.CharField(max_length=150, verbose_name="Nome")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo")
    nivel = models.PositiveSmallIntegerField(choices=NIVEL_CHOICES, verbose_name="Nível hierárquico")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='subordinados', verbose_name="Superior imediato")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Setor do Organograma"
        verbose_name_plural = "Organograma — Setores"
        ordering = ['nivel', 'nome']

    def __str__(self):
        return f"{self.codigo} — {self.nome}"

class Indicator(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nome do Indicador")
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="indicators", verbose_name="Setor")
    is_active = models.BooleanField(default=True, verbose_name="Está ativo?")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição / Fórmula de Cálculo")
    class Meta: verbose_name = "Indicador"; verbose_name_plural = "Indicadores"; ordering = ['sector', 'name']
    def __str__(self): return f"{self.sector.name} - {self.name}"

class IndicatorData(models.Model):
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE, related_name="data_entries", verbose_name="Indicador")
    period = models.DateField(verbose_name="Período") # Nome mantido, mas usado para data diária
    value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Registrado")
    notes = models.TextField(blank=True, null=True, verbose_name="Observações")
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Registrado por")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: verbose_name = "Dado de Indicador"; verbose_name_plural = "Dados de Indicadores"; unique_together = ('indicator', 'period'); ordering = ['-period', 'indicator']
    def __str__(self): return f"{self.indicator.name} - {self.period.strftime('%d/%m/%Y')}: {self.value}"


# --- Recepção: dados adicionais do paciente (CPF/CNS) ---
class PatientExtra(models.Model):
    patient = models.OneToOneField('Patient', on_delete=models.CASCADE, related_name='extra', verbose_name="Paciente")
    cpf = models.CharField(max_length=14, null=True, blank=True, verbose_name="CPF")
    cns = models.CharField(max_length=15, null=True, blank=True, verbose_name="CNS")

    class Meta:
        verbose_name = "Dados Adicionais do Paciente"
        verbose_name_plural = "Dados Adicionais dos Pacientes"

    def __str__(self):
        return f"Extras de {self.patient.name}"


class PatientDocument(models.Model):
    CATEGORY_CHOICES = [
        ('EXAME', 'Exames'),
        ('LAUDO', 'Laudos'),
        ('DOCUMENTO', 'Documentos Pessoais'),
        ('REQUERIMENTO', 'Requerimentos'),
        ('ATESTADO', 'Atestados'),
        ('OUTRO', 'Outros'),
    ]

    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='documents', verbose_name="Paciente")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Categoria")
    description = models.CharField(max_length=255, blank=True, verbose_name="Descrição")
    document = models.FileField(upload_to='patient_documents/%Y/%m/', verbose_name="Arquivo")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Enviado por")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Enviado em")

    class Meta:
        verbose_name = "Documento do Paciente"
        verbose_name_plural = "Documentos do Paciente"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_category_display()} - {self.patient.name}"


# --- NSP: Eventos Adversos ---
class AdverseEventReport(models.Model):
    patient = models.ForeignKey('Patient', on_delete=models.PROTECT, related_name='adverse_event_reports')
    date_evento = models.DateField(verbose_name="Data do evento")
    pulseira_identificacao = models.BooleanField(default=False)
    identificacao_medicacao = models.BooleanField(default=False)
    risco_queda = models.BooleanField(default=False)
    lesao_pressao = models.BooleanField(default=False)
    flebite = models.BooleanField(default=False)
    tempo_acesso_dias = models.PositiveIntegerField(null=True, blank=True)
    tempo_roupa_cama_dias = models.PositiveIntegerField(null=True, blank=True)
    identificacao_leito = models.BooleanField(default=False)
    nao_conformidade_estruturas = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_adverse_reports')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_evento', '-created_at']
        verbose_name = "Evento Adverso"
        verbose_name_plural = "Eventos Adversos"

    def __str__(self):
        return f"{self.patient.name} - {self.date_evento}"


# --- Recepção: Atendimento e Fila ---
class ReceptionAttendance(models.Model):
    patient = models.ForeignKey('Patient', on_delete=models.PROTECT, related_name='reception_attendances', verbose_name="Paciente")
    origin_sector = models.CharField(max_length=100, default='Recepção', verbose_name="Setor de Origem")
    notes = models.TextField(blank=True, null=True, verbose_name="Observações")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    # Identificação / Procedência / Encaminhamento / Documentação / Datas / Outros
    care_type = models.CharField(
        max_length=20,
        choices=[('AMBULATORIO','Ambulatório'),('URGENCIA','Urgência'),('INTERNACAO','Internação'),('EXAME','Exame'),('OUTRO','Outro')],
        default='AMBULATORIO',
        verbose_name="Tipo de atendimento"
    )
    origin = models.CharField(
        max_length=20,
        choices=[('HOSPITAL','Próprio hospital'),('UBS','Unidade Básica de Saúde (UBS)'),('HOSPITAL_EXTERNO','Outro hospital'),('REGULACAO','Regulação estadual'),('OUTRO','Outro')],
        default='HOSPITAL',
        verbose_name="Origem do paciente"
    )
    reason = models.TextField(blank=True, null=True, verbose_name="Motivo da vinda")
    referral_type = models.CharField(
        max_length=20,
        choices=[('ESPONTANEO','Espontâneo'),('REGULADO','Regulado'),('TRANSFERENCIA','Transferência externa')],
        default='ESPONTANEO',
        verbose_name="Tipo de encaminhamento"
    )
    reference_document = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nº guia/senha/referência")
    entry_at = models.DateTimeField(blank=True, null=True, verbose_name="Entrada em")
    triage_at = models.DateTimeField(blank=True, null=True, verbose_name="Triagem em")
    attendance_at = models.DateTimeField(blank=True, null=True, verbose_name="Atendimento em")
    requester_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Profissional solicitante")
    requester_registry = models.CharField(max_length=50, blank=True, null=True, verbose_name="Registro do solicitante")

    class Meta:
        verbose_name = "Atendimento (Recepção)"
        verbose_name_plural = "Atendimentos (Recepção)"
        ordering = ['-created_at']

    def __str__(self):
        return f"Atendimento de {self.patient.name} em {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class ReceptionQueueEntry(models.Model):
    PRIORITY_CHOICES = [
        ('NORMAL', 'Normal'),
        ('PREFERENCIAL', 'Preferencial'),
        ('EMERGENCIA', 'Emergência'),
    ]
    STATUS_CHOICES = [
        ('AGUARDANDO', 'Aguardando'),
        ('CHAMADO', 'Chamado'),
        ('ENCAMINHADO', 'Encaminhado'),
        ('FINALIZADO', 'Finalizado'),
    ]

    attendance = models.ForeignKey('ReceptionAttendance', on_delete=models.CASCADE, related_name='queue_entries', verbose_name="Atendimento")
    destination_sector = models.CharField(max_length=100, verbose_name="Setor de Destino")
    priority = models.CharField(max_length=15, choices=PRIORITY_CHOICES, default='NORMAL', verbose_name="Prioridade")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='AGUARDANDO', verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    called_at = models.DateTimeField(blank=True, null=True, verbose_name="Chamado em")
    finished_at = models.DateTimeField(blank=True, null=True, verbose_name="Finalizado em")

    class Meta:
        verbose_name = "Entrada de Fila (Recepção)"
        verbose_name_plural = "Fila de Espera (Recepção)"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.attendance.patient.name} - {self.get_priority_display()} - {self.get_status_display()}"
