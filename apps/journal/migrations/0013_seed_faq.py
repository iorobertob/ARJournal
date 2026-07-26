"""Seed the FAQ page with the stakeholder-supplied questions and answers.

Only fills the field if it is currently blank, so it never overwrites content
an editor has already saved through the dashboard (safe to run on production).
"""
from django.db import migrations


FAQ_HTML = """
<h2>Who can submit to InAct?</h2>
<p>We welcome submissions from artist-researchers, scholars, practitioners, and collaborative research teams working across disciplines, sectors, and creative practices.</p>

<h2>What types of contributions does the journal accept?</h2>
<p>The journal publishes original research articles, artistic research projects, practice-based research, interdisciplinary studies, and submissions that combine scholarly and artistic forms of inquiry.</p>

<h2>What is the recommended length of a submission?</h2>
<p>The recommended length is 20,000&ndash;40,000 characters, including spaces (approximately 3,000&ndash;6,000 words). Artistic research submissions must include a written component of at least 10,000 characters.</p>

<h2>Can I submit audio, video, scores, or other artistic materials?</h2>
<p>Yes. Authors may submit supplementary materials such as scores, audio recordings, video recordings, visual documentation, datasets, and other artistic research outputs. All materials should be clearly labelled and accompanied by appropriate descriptions.</p>

<h2>How do I submit my manuscript?</h2>
<p>All submissions must be made through the journal platform.</p>

<h2>What submission formats are supported?</h2>
<p>Authors may submit manuscripts in one of two ways:</p>
<p><strong>Browser-based editor</strong></p>
<ul>
<li>Write and edit directly within the online platform.</li>
<li>Supports embedded images, audio, video, footnotes, citations, and LaTeX equations.</li>
<li>Particularly suitable for multimedia and artistic research submissions.</li>
</ul>
<p><strong>LaTeX submission</strong></p>
<ul>
<li>Upload a LaTeX manuscript prepared offline using tools such as Overleaf or LaTeX Workshop for VS Code.</li>
<li>Supports .bib bibliography files, custom macros, and complex mathematical notation.</li>
<li>Media files must be uploaded separately according to the journal&rsquo;s LaTeX template requirements.</li>
</ul>

<h2>Is a cover letter required?</h2>
<p>Yes. Every submission must be accompanied by a short cover letter describing the contribution of the work, its relevance to the journal&rsquo;s aims and scope, and confirming that the manuscript is original and not under consideration elsewhere.</p>

<h2>Do I need to provide a biography and photograph?</h2>
<p>Yes. Authors should provide a short biography (50&ndash;150 words) and a recent high-resolution portrait photograph.</p>

<h2>What citation style should I use?</h2>
<p>InAct follows the Cambridge author-date referencing system. Full details are available in the Author Guidelines.</p>

<h2>Can I use AI tools when preparing my submission?</h2>
<p>Authors may use AI-assisted tools for research support, language editing, translation, or similar purposes, provided that any significant use is clearly disclosed. Authors remain fully responsible for the accuracy, originality, and integrity of their work.</p>

<h2>What type of peer review does the journal use?</h2>
<p>InAct operates a double-blind peer-review process. Each submission is reviewed by at least two independent reviewers.</p>

<h2>How long does the review process take?</h2>
<p>Reviewers are normally given two to three months to complete their reviews. The editorial team will inform authors of the outcome as soon as the review process has been completed.</p>

<h2>Is there a submission fee or article processing charge (APC)?</h2>
<p>No. InAct does not charge submission fees, article processing charges, or publication fees.</p>

<h2>Does the journal provide translation or language-editing services?</h2>
<p>No. Manuscripts must be submitted in English, and authors are responsible for ensuring the linguistic quality of their submissions.</p>

<h2>Is InAct an open-access journal?</h2>
<p>Yes. All content is published under a Libre Open Access model and is freely accessible online without subscription fees.</p>

<h2>May I submit a manuscript that has been published elsewhere?</h2>
<p>No. InAct only accepts original work that has not been previously published and is not under consideration by another publication.</p>

<h2>Does the journal remunerate authors for submissions?</h2>
<p>No.</p>

<h2>How often is the journal published?</h2>
<p>One volume is published annually.</p>
""".strip()


def seed(apps, schema_editor):
    JournalConfig = apps.get_model('journal', 'JournalConfig')
    journal = JournalConfig.objects.first()
    if journal is None:
        return
    if not journal.faq_text:
        journal.faq_text = FAQ_HTML
        journal.save(update_fields=['faq_text'])


def unseed(apps, schema_editor):
    # Non-destructive reverse: leave content in place.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0012_journalconfig_faq_text'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
