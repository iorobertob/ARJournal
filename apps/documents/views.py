from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from .models import CanonicalDocument


@login_required
def canonical_document_json(request, pk):
    doc = get_object_or_404(CanonicalDocument, pk=pk)
    submission = doc.revision.submission
    if submission.author_id != request.user.id and not request.user.has_editorial_access():
        return HttpResponseForbidden()
    return JsonResponse(doc.data)
