from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from .models import Issue, EditorialBoardMember, JournalConfig


def home(request):
    current_issue = Issue.objects.filter(is_current=True, is_published=True).first()
    if not current_issue:
        current_issue = Issue.objects.filter(is_published=True).first()
    recent_issues = Issue.objects.filter(is_published=True).exclude(
        pk=current_issue.pk if current_issue else -1
    )[:3]
    from apps.production.models import HTMLBuild
    featured_articles = []
    if current_issue:
        featured_articles = (
            HTMLBuild.objects
            .filter(is_published=True, document__revision__submission__issue=current_issue)
            .select_related('document__revision__submission')[:8]
        )
    return render(request, 'public/home.html', {
        'current_issue': current_issue,
        'featured_articles': featured_articles,
        'recent_issues': recent_issues,
    })


def issue_detail(request, number):
    issue = get_object_or_404(Issue, number=number, is_published=True)
    from apps.production.models import HTMLBuild
    articles = (
        HTMLBuild.objects
        .filter(is_published=True, document__revision__submission__issue=issue)
        .select_related('document__revision__submission__author__profile')
        .order_by('document__revision__submission__issue_order')
    )
    return render(request, 'public/issue.html', {'issue': issue, 'articles': articles})


def article_detail(request, slug):
    from apps.production.models import HTMLBuild
    build = get_object_or_404(HTMLBuild, slug=slug, is_published=True)
    submission = build.document.revision.submission
    toc = build.table_of_contents or []
    return render(request, 'public/article.html', {
        'build': build,
        'submission': submission,
        'toc': toc,
    })


def archive(request):
    issues = Issue.objects.filter(is_published=True)
    return render(request, 'public/archive.html', {'issues': issues})


def about(request):
    board = EditorialBoardMember.objects.filter(is_active=True)
    return render(request, 'public/about.html', {'board': board})


def submit_info(request):
    return render(request, 'public/submit.html', {})


def author_page(request, pk):
    from apps.accounts.models import User, UserProfile
    author = get_object_or_404(User, pk=pk)
    from apps.production.models import HTMLBuild
    articles = (
        HTMLBuild.objects
        .filter(is_published=True, document__revision__submission__author=author)
        .select_related('document__revision__submission')
    )
    return render(request, 'public/author_page.html', {'author': author, 'articles': articles})


def download_template(request):
    """Serve the LaTeX template pack as a zip download."""
    import zipfile, io, os
    from django.http import HttpResponse
    from django.conf import settings
    template_dir = settings.BASE_DIR / 'template_pack'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in os.listdir(template_dir):
            fpath = template_dir / fname
            if fpath.is_file():
                zf.write(fpath, fname)
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="transact_author_template.zip"'
    return response
