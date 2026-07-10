from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .models import Alerte


@login_required
@require_POST
def marquer_lu(request, pk):
    alerte = get_object_or_404(Alerte, pk=pk)
    alerte.lu = True
    alerte.save(update_fields=['lu'])
    return JsonResponse({'ok': True})


@login_required
@require_POST
def marquer_tout_lu(request):
    Alerte.objects.filter(lu=False).update(lu=True)
    return JsonResponse({'ok': True})
