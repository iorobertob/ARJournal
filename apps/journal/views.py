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
    from apps.submissions.models import Submission, SubmissionStatus
    from .models import Section

    submissions = (
        Submission.objects
        .filter(
            issue=issue,
            status__in=[
                SubmissionStatus.ACCEPTED,
                SubmissionStatus.IN_PRODUCTION,
                SubmissionStatus.PUBLISHED,
            ]
        )
        .select_related('author', 'section')
        .prefetch_related('revisions__canonical_document__html_build')
        .order_by('issue_order')
    )

    def _build_entry(sub):
        rev = sub.get_current_revision()
        build = None
        if rev:
            try:
                doc = rev.canonical_document
                build = getattr(doc, 'html_build', None)
                if build and not build.is_published:
                    build = None
            except Exception:
                pass
        return {'submission': sub, 'build': build}

    # Evaluate queryset once, build all entries
    all_entries = [_build_entry(s) for s in submissions]

    # Group by section (ordered sections first, then unsectioned)
    sections = list(issue.sections.all())
    sectioned_pks = set()
    section_groups = []
    for section in sections:
        entries = [e for e in all_entries if e['submission'].section_id == section.pk]
        if entries:
            section_groups.append({'section': section, 'articles': entries})
            sectioned_pks.update(e['submission'].pk for e in entries)
    unsectioned_articles = [e for e in all_entries if e['submission'].pk not in sectioned_pks]

    return render(request, 'public/issue.html', {
        'issue': issue,
        'section_groups': section_groups,
        'unsectioned_articles': unsectioned_articles,
        'articles': all_entries,
    })


def article_detail(request, slug):
    from apps.production.models import HTMLBuild
    build = get_object_or_404(HTMLBuild, slug=slug, is_published=True)
    submission = build.document.revision.submission
    toc = build.table_of_contents or []

    # DOI (if deposited)
    doi = None
    try:
        dep = build.document.doi_deposit
        if dep.status in ('deposited', 'registered') and dep.doi:
            doi = dep.doi
    except Exception:
        pass

    article_url = request.build_absolute_uri()
    identifier = f'https://doi.org/{doi}' if doi else article_url

    # Author name parts for citation formatting
    author = submission.author
    first = author.first_name or ''
    last = author.last_name or ''
    display = author.display_name

    if last and first:
        apa_author     = f'{last}, {first[0]}.'
        mla_author     = f'{last}, {first}'
        chicago_author = f'{first} {last}'
        bibtex_author  = f'{last}, {first}'
        bibtex_key     = last.lower()
    else:
        apa_author = mla_author = chicago_author = bibtex_author = display
        bibtex_key = display.split()[0].lower() if display else 'author'

    journal = JournalConfig.get()
    jname   = journal.name
    title   = submission.title
    year    = submission.issue.year    if submission.issue else ''
    volume  = submission.issue.volume  if submission.issue else ''
    number  = submission.issue.number  if submission.issue else ''
    bk      = f'{bibtex_key}{year}'

    vol_issue = f', {volume}({number})' if (volume and number) else ''

    citations = {
        'apa': (
            f'{apa_author} ({year}). {title}. {jname}{vol_issue}. {identifier}'
        ),
        'mla': (
            f'{mla_author}. "{title}." {jname}, vol.\u00a0{volume}, '
            f'no.\u00a0{number}, {year}, {identifier}.'
        ),
        'chicago': (
            f'{chicago_author}. "{title}." {jname} {volume}, '
            f'no.\u00a0{number} ({year}). {identifier}.'
        ),
        'bibtex': (
            f'@article{{{bk},\n'
            f'  author  = {{{bibtex_author}}},\n'
            f'  title   = {{{{{title}}}}},\n'
            f'  journal = {{{jname}}},\n'
            f'  year    = {{{year}}},\n'
            f'  volume  = {{{volume}}},\n'
            f'  number  = {{{number}}},\n'
            f'  url     = {{{identifier}}},\n'
            f'}}'
        ),
    }

    return render(request, 'public/article.html', {
        'build': build,
        'submission': submission,
        'toc': toc,
        'doi': doi,
        'article_url': article_url,
        'cite_apa':     citations['apa'],
        'cite_mla':     citations['mla'],
        'cite_chicago': citations['chicago'],
        'cite_bibtex':  citations['bibtex'],
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
