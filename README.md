# Documentação HRRO_CORE

## Stack e módulos
- **Backend:** Django 5 + PostgreSQL.
- **Frontend:** Templates Django + Tailwind via CDN + Chart.js + Lucide.
- **PDF:** WeasyPrint (relatórios NSP e Fisioterapia).
- **Apps principais:**
  - `core` — gestão geral, NIR (leitos/internações), NSP (indicadores/eventos adversos), recepção, exames.
  - `app.fisioterapia` — painel assistencial e coordenação, relatórios diários, gestão de equipe.
- **Importações:** comandos de management para carga de leitos e internações via `ocupacao.csv`.

**HRRO_CORE — Sistema Hospitalar Integrado**  
Documentação Técnica – Versão 1.1  
Autor: Uélinton Quintão Silvério

---

## Índice
1. Introdução  
1.1 Objetivo Geral  
1.2 Objetivos Específicos  
1.3 Escopo do Sistema  
2. Fragilidades e Dificuldades Encontradas  
2.1 Fragmentação e Ausência de Sistema Unificado  
3. Funcionalidades Principais  
4. Arquitetura de Alto Nível  
4.1 Componentes Principais  
4.2 Serviços Complementares (Futuro)  
5. Fluxo Operacional  
6. Modelo de Dados  
7. Requisitos do Sistema  
8. Considerações Finais  

---

## 1. Introdução
O **HRRO_CORE** é um sistema desenvolvido para unificar e automatizar processos hospitalares críticos, com foco em regulação de leitos (NIR), segurança do paciente (NSP), recepção e fisioterapia.

**Importante:** o sistema foi projetado com foco em rastreabilidade, padronização, segurança e governança assistencial.

### 1.1 Objetivo Geral
Prover uma plataforma única para gestão de:
- Leitos e internações;
- Indicadores de segurança do paciente;
- Registro de eventos adversos;
- Fluxos de recepção e fila;
- Relatórios operacionais de fisioterapia.

### 1.2 Objetivos Específicos
- Centralizar dados assistenciais;
- Automatizar fluxos críticos;
- Gerar inteligência operacional;
- Facilitar auditorias e relatórios.

### 1.3 Escopo do Sistema
O HRRO_CORE cobre a gestão hospitalar essencial e está preparado para expansão futura com novos módulos e integrações.

---

## 2. Fragilidades e Dificuldades Encontradas
O diagnóstico inicial mostrou fragilidades comuns em ambientes hospitalares:

### 2.1 Fragmentação e Ausência de Sistema Unificado
Problemas identificados:
- Uso de planilhas desconectadas;
- Falta de histórico estruturado;
- Informações duplicadas;
- Baixa rastreabilidade;
- Dependência de conhecimento individual.

---

## 3. Funcionalidades Principais
- **NIR:** mapa de leitos, internações, alta de pacientes.
- **NSP:** dashboard de indicadores, checklist de eventos adversos, exportação de relatórios em PDF.
- **Recepção:** cadastro, fila e fluxos de atendimento.
- **Fisioterapia:**
  - Assistencial: criação/edição de relatórios diários;
  - Coordenação: dashboard, CRUD completo de relatórios;
  - Exportação em PDF por relatório e em lote;
  - Gestão de equipe (ativar/desativar, auditoria e reativação).

---

## 4. Arquitetura de Alto Nível
A arquitetura é modular, baseada em Django, com separação por apps e templates.

### 4.1 Componentes Principais
**Frontend Web**
- Templates Django;
- Tailwind via CDN;
- Chart.js para gráficos;
- UI responsiva.

**Backend**
- Regras de negócio (NIR/NSP/Recepção/Fisio);
- Autenticação e permissões;
- Integração com banco PostgreSQL.

**Banco de Dados**
- PostgreSQL;
- Entidades principais:
  - `Patient`, `Bed`, `Hospitalization`;
  - `AdverseEventReport`;
  - `FisioReport`, `FisioReportProcedure`, `FisioUserAudit`;
  - `ReceptionAttendance`, `ReceptionQueueEntry`.

### 4.2 Serviços Complementares (Futuro)
- Integração com sistemas externos;
- BI/Analytics;
- Alertas e automações;
- Novos módulos clínicos.

---

## 5. Fluxo Operacional
1. Cadastro de pacientes / recepção;
2. Internação e gestão de leitos;
3. Registro de eventos adversos;
4. Relatórios diários de fisioterapia;
5. Dashboards e indicadores.

---

## 6. Modelo de Dados
Tabelas principais:
- Paciente (`Patient`);
- Leito (`Bed`);
- Internação (`Hospitalization`);
- Evento Adverso (`AdverseEventReport`);
- Relatório Fisioterapia (`FisioReport`).

---

## 7. Requisitos do Sistema
### Requisitos Técnicos
- Python 3.11+;
- Django 5.x;
- PostgreSQL;
- WeasyPrint para PDFs;
- Ambiente Windows ou Linux.

### Requisitos Operacionais
- Usuários com perfil adequado;
- Procedimentos internos padronizados.

---

## 8. Considerações Finais
O HRRO_CORE consolida uma base moderna para gestão hospitalar, com foco em segurança, rastreabilidade e eficiência operacional.

Documento desenvolvido por **Uélinton Quintão Silvério** — Autor e idealizador do sistema HRRO_CORE.
