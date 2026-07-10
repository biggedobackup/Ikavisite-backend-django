from .models import Alerte


def alertes_non_lues(request):
    try:
        if not request.user.is_authenticated:
            return {}
    except Exception:
        return {}
    nb = Alerte.objects.filter(lu=False).count()
    alertes = Alerte.objects.filter(lu=False)[:20]
    return {
        'alertes_non_lues': alertes,
        'nb_alertes_non_lues': nb,
    }
