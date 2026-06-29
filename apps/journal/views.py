from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from .models import Issue, EditorialBoardMember, FeaturedSelection, JournalConfig, ArticleType


def home(request):
    from apps.production.models import HTMLBuild
    from apps.submissions.models import Submission, SubmissionStatus

    current_issue = Issue.objects.filter(is_current=True, is_published=True).first()
    if not current_issue:
        current_issue = Issue.objects.filter(is_published=True).first()

    # Current-issue table of contents (left column of the hero block)
    toc_editorial, toc_articles = [], []
    issue_builds = []
    if current_issue:
        submissions = (
            Submission.objects
            .filter(
                issue=current_issue,
                status__in=[
                    SubmissionStatus.ACCEPTED,
                    SubmissionStatus.IN_PRODUCTION,
                    SubmissionStatus.PUBLISHED,
                ],
            )
            .select_related('author')
            .order_by('issue_order')
        )
        for sub in submissions:
            (toc_editorial if sub.article_type == ArticleType.EDITORIAL else toc_articles).append(sub)

        issue_builds = list(
            HTMLBuild.objects
            .filter(is_published=True, document__revision__submission__issue=current_issue)
            .select_related('document__revision__submission__author',
                            'document__revision__submission__issue')
        )

    # "Across the archive" — rotating featured selection
    selection = FeaturedSelection.current()
    featured_archive = (
        selection.articles.select_related(
            'document__revision__submission__author',
            'document__revision__submission__issue',
        )
        if selection else []
    )

    # Filter panel data
    years = (
        Issue.objects.filter(is_published=True)
        .values_list('year', flat=True).distinct().order_by('-year')
    )
    categories = ArticleType.choices

    return render(request, 'public/home.html', {
        'current_issue': current_issue,
        'toc_editorial': toc_editorial,
        'toc_articles': toc_articles,
        'issue_builds': issue_builds,
        'featured_archive': featured_archive,
        'filter_years': years,
        'filter_categories': categories,
    })


def news(request):
    return render(request, 'public/news.html', {
        'issues': Issue.objects.filter(is_published=True).exclude(call_for_submissions='')[:10],
    })


def contact(request):
    return render(request, 'public/contact.html', {})


def partners(request):
    return render(request, 'public/partners.html', {})


def imprint(request):
    return render(request, 'public/imprint.html', {})


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
    from django.db.models import Q
    from apps.production.models import HTMLBuild

    q = request.GET.get('q', '').strip()
    issues = Issue.objects.filter(is_published=True).order_by('-year', '-number')
    results = None
    if q:
        # Comma-separated terms are OR'ed; a 4-digit term also matches the issue year
        terms = [t.strip() for t in q.split(',') if t.strip()]
        cond = Q()
        for term in terms:
            term_cond = (
                Q(document__revision__submission__title__icontains=term) |
                Q(document__revision__submission__subtitle__icontains=term) |
                Q(document__revision__submission__author__first_name__icontains=term) |
                Q(document__revision__submission__author__last_name__icontains=term) |
                Q(document__revision__submission__keywords__icontains=term)
            )
            if term.isdigit() and len(term) == 4:
                term_cond |= Q(document__revision__submission__issue__year=int(term))
            cond |= term_cond
        results = (
            HTMLBuild.objects
            .filter(is_published=True)
            .filter(cond)
            .select_related(
                'document__revision__submission__author',
                'document__revision__submission__issue',
            )
            .order_by('-published_at')
        )
    return render(request, 'public/archive.html', {
        'issues': issues,
        'results': results,
        'q': q,
    })


def about(request):
    board = EditorialBoardMember.objects.filter(is_active=True)
    return render(request, 'public/about.html', {'board': board})


def submit_info(request):
    return render(request, 'public/submit.html', {})


def author_page(request, pk):
    from apps.accounts.models import User, UserProfile
    author = get_object_or_404(User, pk=pk, is_active=True)
    from apps.production.models import HTMLBuild
    articles = (
        HTMLBuild.objects
        .filter(is_published=True, document__revision__submission__author=author)
        .select_related('document__revision__submission')
    )
    return render(request, 'public/author_page.html', {'author': author, 'articles': articles})


def terms(request):
    return render(request, 'public/terms.html', {})


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
    response['Content-Disposition'] = 'attachment; filename="inact_author_template.zip"'
    return response
