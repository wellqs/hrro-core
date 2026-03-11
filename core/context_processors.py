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
