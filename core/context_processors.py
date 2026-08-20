from .models import OrgUnit, ORG_TIPO_COLORS

# Ordem e rótulos dos grupos do organograma na sidebar (mesma organização do modelo SaúdeGestão RO)
ORG_SIDEBAR_GROUPS = [
    ('direcao', 'Direção'),
    ('diretoria', 'Diretorias'),
    ('gerencia', 'Gerências'),
    ('assistencial', 'Assistenciais'),
    ('administrativo', 'Administrativos'),
    ('unidade', 'Unidades'),
    ('comissao', 'Comissões'),
    ('nucleo', 'Núcleos'),
]


def _group_names(user):
    if not user.is_authenticated:
        return set()
    return {name.upper() for name in user.groups.values_list("name", flat=True)}


def _has_keyword(group_names, keyword):
    key = keyword.upper()
    return any(key in name for name in group_names)


def sector_access(request):
    user = request.user
    group_names = _group_names(user)

    can_nsp = user.is_superuser or _has_keyword(group_names, "NSP")
    can_nir = user.is_superuser or _has_keyword(group_names, "NIR")
    can_reception = user.is_superuser or _has_keyword(group_names, "RECEP")
    can_fisio_coord = user.is_superuser or "FISIOTERAPIA COORDENADOR" in group_names
    can_fisio_assist = user.is_superuser or "FISIOTERAPIA ASSISTENCIAL" in group_names
    can_fisio = can_fisio_coord or can_fisio_assist or _has_keyword(group_names, "FISIOTERAPIA")

    return {
        "can_nsp": can_nsp,
        "can_nir": can_nir,
        "can_reception": can_reception,
        "can_fisio": can_fisio,
        "can_fisio_coord": can_fisio_coord,
    }


def org_sidebar(request):
    """Organograma agrupado por setor (Direção, Gerências, ...) para a sidebar."""
    if not request.user.is_authenticated:
        return {}

    resolver_match = getattr(request, "resolver_match", None)
    current_codigo = resolver_match.kwargs.get("codigo") if resolver_match else None

    units_by_tipo = {}
    for unit in OrgUnit.objects.filter(is_active=True).order_by("nome"):
        units_by_tipo.setdefault(unit.tipo, []).append(unit)

    groups = []
    for tipo, label in ORG_SIDEBAR_GROUPS:
        group_units = units_by_tipo.get(tipo, [])
        if not group_units:
            continue
        groups.append({
            "id": tipo,
            "label": label,
            "color": ORG_TIPO_COLORS.get(tipo, "#64748b"),
            "units": group_units,
            "active": any(unit.codigo == current_codigo for unit in group_units),
        })

    return {
        "sidebar_org_groups": groups,
        "sidebar_org_current": current_codigo,
    }
