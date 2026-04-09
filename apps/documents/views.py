from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import CanonicalDocument


@login_required
def canonical_document_json(request, pk):
    doc = get_object_or_404(CanonicalDocument, pk=pk)
    return JsonResponse(doc.data)
