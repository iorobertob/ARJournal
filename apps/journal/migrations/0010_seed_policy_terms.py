"""Seed the Policy page and the Terms & Conditions page with their initial
stakeholder-supplied text.

Only fills a field that is currently blank, so it never overwrites content that
an editor has already saved through the dashboard (safe to run on production).
The Terms text is the previous hardcoded page merged with the corrected §4
licence (CC BY-NC-ND 4.0); journal name / email / institution are baked in from
the live JournalConfig at migration time.
"""
from django.db import migrations


POLICY_HTML = """
<h2>Open Access</h2>
<p>InAct is published under a Libre Open Access model. This model of scholarly communication ensures free, immediate and online access to academic articles for all users without restriction. It allows for unrestricted reading, downloading, copying, sharing, storing, printing, searching and hyperlinking, in accordance with the terms of the Creative Commons license (CC BY-NC-ND 4.0: Attribution &ndash; NonCommercial &ndash; NoDerivatives).</p>
<p>The CC BY-NC-ND 4.0/International license is a publicly available legal framework that defines the permitted scope of use of a Work.</p>
<p>Under this licence, any individual may:</p>
<ul>
<li><strong>Share</strong> &ndash; reproduce and distribute the Work in any medium or format,</li>
<li>Include the Work in a collective publication (e.g. as part of a compendium),</li>
</ul>
<p>provided the following conditions are met:</p>
<ul>
<li><strong>Attribution</strong> &ndash; the original work must be properly cited, including the title, author, source (InAct) and the licence used (with a link to the full text of the CC BY-NC-ND 4.0 International licence conditions),</li>
<li><strong>NonCommercial use only</strong> &ndash; the work may not be used for commercial purposes,</li>
<li><strong>NoDerivatives</strong> &ndash; any edited, supplemented or otherwise modified version of the Work may not be redistributed.</li>
</ul>
<p>The full text of the licence terms is available here: <a href="https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.en">https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.en</a></p>

<h2>Editing Services</h2>
<p>Authors are responsible for ensuring the quality and accuracy of the language in their submissions.</p>

<h2>Data Sharing Policy</h2>
<p>The journal encourages authors to make the data underlying their research publicly available where possible. Sharing data promotes transparency, reproducibility, and the wider dissemination of knowledge.</p>
<p>Authors should deposit their data in appropriate, recognised repositories and provide a clear data availability statement within their submission. Where data cannot be shared due to ethical, legal, or confidentiality constraints, authors must clearly state the reasons.</p>
<p>Any shared data should be properly documented to ensure that it can be understood and reused by other researchers. Authors remain responsible for ensuring that data sharing complies with relevant regulations, including data protection and privacy requirements.</p>

<h2>Publication Charges and Remuneration</h2>
<p>No fees are charged for the submission, processing, or publication of manuscripts. Authors do not receive any remuneration for publishing.</p>
<p>Securing licensing rights for images used in a manuscript, translations into a foreign language, and other requirements necessary for publication are handled in agreement with the editorial team. These responsibilities rest primarily with the author.</p>

<h2>Publication Ethics and Malpractice Statement</h2>

<h3>Research Ethics</h3>
<p>All submissions must adhere to recognised ethical standards in research and publication. Authors are responsible for ensuring that their work complies with relevant institutional and national regulations. Research involving human participants, animals, or sensitive data must have received appropriate ethical approval prior to the study being conducted. Informed consent must be obtained where applicable, and participants&rsquo; rights, dignity, and privacy must always be respected.</p>
<p>Authors must ensure the accuracy, integrity, originality, and transparency of their work. Any significant use of artificial intelligence (AI) tools in the research, writing, editing, translation, data analysis, or preparation of a manuscript must be clearly disclosed. AI tools cannot be listed as authors, and authors remain fully responsible for the content of their submissions.</p>
<p>Plagiarism, data fabrication, falsification, undisclosed AI-generated content presented as original scholarship, and other forms of academic misconduct are strictly prohibited.</p>

<h3>Publication and Authorship</h3>
<p>Editing and publication of the journal InAct follows established principles of academic ethics.</p>
<ul>
<li>Articles previously published elsewhere are not accepted for publication.</li>
<li>Plagiarism, i.e. wrong appropriation of somebody else&rsquo;s text, research methodology, ideas, or results, or presentation of empiric data that has already been introduced into scholarly circulation as new and freshly discovered, or purposeful neglect of proper references is prohibited.</li>
<li>Authors retain copyright to their work while granting InAct the right to publish and distribute it under the terms of the CC BY-NC-ND 4.0 licence.</li>
<li>In case of special circumstances causing termination of the journal&rsquo;s publication, the archive of the former issues is to be preserved and freely available on the Institute&rsquo;s website.</li>
<li>Publication of articles in the journal is free of charge. Authors are not entitled for any financial remuneration for their contributions.</li>
</ul>

<h3>Author Responsibilities</h3>
<ul>
<li>Manuscripts submitted for publication must meet the requirements of research publications and follow the editing principles specified in the Author Guidelines.</li>
<li>All authors listed on a paper must have made substantive contributions to the research and writing of the paper.</li>
<li>Authors must make sure that all data cited in the article are, to the best of their knowledge, real, accurate, and authentic.</li>
<li>Authors must make sure that all sources of financial support for research connected to a paper are acknowledged on publication.</li>
<li>Authors are required to take into account the reviewers&rsquo; comments regarding soundness of their statements and conclusions, the level of analysis, and other motivated reviewers&rsquo; opinions, and correct the indicated mistakes.</li>
</ul>

<h3>Peer Review and Reviewer Responsibilities</h3>
<p>Research articles submitted for publication in InAct are reviewed using peer review method by at least two anonymous reviewers, selected by the Editorial Board from the specialists in the corresponding field. If the reviewers present contrary opinions regarding suitability of the article for publication, the Editorial Board appoints a third reviewer, and after receiving their conclusions, makes the final decision.</p>
<p>The process of reviewing is double-blind, i.e. the reviewers are not aware of the authors&rsquo; identity, and vice versa.</p>
<ul>
<li>The reviewers must disclose to the special editor or the Editorial Board any potential conflicts of interest regarding the manuscripts they are asked to referee, including concerns related to funding or their personal objections to the material in question.</li>
<li>Reviewers must alert the Editorial Board to any similar or related work already published, which is not cited in the paper in question.</li>
<li>Reviewers should treat manuscripts under review as confidential materials. They must not discuss, distribute, or in any way retain copies of manuscripts reviewed.</li>
</ul>

<h3>Editorial Responsibilities</h3>
<ul>
<li>Editorial Board has final authority to accept or reject a submission.</li>
<li>Editors are responsible for recognizing any potential conflict of interest with regard to a submission and should take appropriate action to ensure that these conflicts do not affect a submission&rsquo;s acceptance or rejection.</li>
<li>Editorial Board has to ensure an appropriate level of peer-reviewing and make unbiased decisions with no regard of possible inequity on the part of the reviewers, connected to the author&rsquo;s gender, sexual orientation, religion, political views, and ethnic / geographical background.</li>
<li>Acceptance of a paper for publication implies confidence in and certainty (to the greatest extent possible) of the validity of the research contained therein.</li>
<li>If a material error is discovered in a published paper, the Editorial Board has to ensure that a correction, retraction, or apology, as appropriate and feasible, is published promptly.</li>
</ul>

<h3>Identification of Unethical Behaviour</h3>
<p>Misconduct and unethical behaviour may be identified and brought to the attention of the editor and publisher at any time, by anyone. Misconduct and unethical behaviour may include, but need not be limited to, examples as outlined above.</p>
<p>Whoever informs the editor or publisher of such conduct should provide sufficient information and evidence in order for an investigation to be initiated. All allegations should be taken seriously and treated in the same way, until a successful decision or conclusion is reached.</p>

<h3>Investigation Procedures</h3>
<ul>
<li>Minor misconduct might be dealt with without the wider consultation with author given the chance to respond to any allegations.</li>
<li>In case of serious misconduct, the editor, in consultation with the publisher or Consortium as appropriate, should make the decision whether or not to involve the employers, either by examining the available evidence themselves or by further consultation with a limited number of experts.</li>
</ul>

<h3>Outcomes</h3>
<ul>
<li>In case of misconduct, the author or reviewer should be informed where there appears to be a misunderstanding or misapplication of acceptable standards.</li>
<li>The author or reviewer could be given a more strongly worded letter as a warning to future behaviour.</li>
<li>A formal notice detailing the misconduct could be published.</li>
<li>A formal letter could be given to the head of the author&rsquo;s or reviewer&rsquo;s department or funding agency.</li>
<li>Formal retraction or withdrawal of a publication from the journal, in conjunction with informing the head of the author or reviewer&rsquo;s department, Abstracting &amp; Indexing services and the readership of the publication.</li>
<li>The case could be reported to a professional organisation or higher authority for further investigation and action.</li>
</ul>
""".strip()


# Terms body — placeholders [[NAME]] / [[EMAIL]] / [[INSTITUTION]] / [[COUNTRY]]
# are replaced with the live JournalConfig values at migration time.
TERMS_HTML = """
<p>These Terms and Conditions govern your use of <strong>[[NAME]]</strong> and all services operated under it, including article submission, peer review, account management, and access to published content. By using this platform you agree to these terms. The effective date of this version is 2025.</p>
<p>Questions or requests relating to these terms should be directed to <a href="mailto:[[EMAIL]]">[[EMAIL]]</a>.</p>

<h2>1. Data We Collect</h2>
<p>We collect only the data necessary to operate the journal. The categories are:</p>
<table>
<thead><tr><th scope="col">Category</th><th scope="col">Examples</th><th scope="col">Purpose</th></tr></thead>
<tbody>
<tr><td>Account data</td><td>Name, email, institution, biography, ORCID iD, profile photo</td><td>Identity, author attribution, correspondence</td></tr>
<tr><td>Submission data</td><td>Manuscript files, metadata, revision history, correspondence with editors</td><td>Peer review, editorial decision, publication</td></tr>
<tr><td>Review data</td><td>Reviewer identity (where open review), review text, recommendations</td><td>Editorial quality assurance, scholarly record</td></tr>
<tr><td>Published article metadata</td><td>Author name, title, abstract, keywords, DOI, publication date</td><td>Permanent scholarly record, citation indexing</td></tr>
<tr><td>Usage data</td><td>Server logs (IP address, browser type, pages visited)</td><td>Security, platform diagnostics</td></tr>
</tbody>
</table>
<p>We do not sell personal data to third parties.</p>

<h2>2. Lawful Basis &amp; Retention</h2>
<table>
<thead><tr><th scope="col">Data</th><th scope="col">Lawful basis (GDPR Art. 6)</th><th scope="col">Retention</th></tr></thead>
<tbody>
<tr><td>Account data</td><td>Contract (submission agreement); consent (registration)</td><td>Until account deletion request; indefinitely where publication record requires it (see &sect;7)</td></tr>
<tr><td>Submission &amp; review data</td><td>Contract; legitimate interest (scholarly integrity)</td><td>7 years after final editorial decision</td></tr>
<tr><td>Published article metadata</td><td>Legitimate interest; public interest archiving (Art. 17(3)(d))</td><td>Permanently &mdash; forms part of the scholarly record</td></tr>
<tr><td>Server logs</td><td>Legitimate interest (security)</td><td>90 days</td></tr>
</tbody>
</table>

<h2>3. Your Rights Under GDPR</h2>
<p>If you are in the European Economic Area, you have the following rights under the General Data Protection Regulation (EU) 2016/679:</p>
<ul>
<li><strong>Right of access (Art. 15)</strong> &mdash; request a copy of the personal data we hold about you.</li>
<li><strong>Right to rectification (Art. 16)</strong> &mdash; request correction of inaccurate data, including a name change on published articles (see &sect;7).</li>
<li><strong>Right to erasure (Art. 17)</strong> &mdash; request deletion of your personal data. Note: where you have published articles, the public interest exception (Art. 17(3)(d)) applies to the publication record; see &sect;7 for what this means in practice.</li>
<li><strong>Right to data portability (Art. 20)</strong> &mdash; request your data in a structured, machine-readable format.</li>
<li><strong>Right to restriction (Art. 18)</strong> &mdash; request that we limit processing of your data in certain circumstances.</li>
<li><strong>Right to object (Art. 21)</strong> &mdash; object to processing based on legitimate interest.</li>
</ul>
<p>To exercise any of these rights, email <a href="mailto:[[EMAIL]]">[[EMAIL]]</a>. We will respond within 30 days. You also have the right to lodge a complaint with the supervisory authority in your country of residence.</p>

<h2>4. Article Submission &amp; Copyright</h2>
<p>By submitting a manuscript to [[NAME]] you confirm that:</p>
<ul>
<li>The work is original, has not been published elsewhere, and is not currently under review at another venue.</li>
<li>All co-authors have approved the submission.</li>
<li>You hold the rights to all content submitted, including images and third-party materials.</li>
<li>You grant [[NAME]] the right to publish, reproduce, and distribute the article in print and digital form.</li>
<li>Copyright in the article remains with the author(s). Published articles are made available under a Creative Commons Attribution&ndash;NonCommercial&ndash;NoDerivatives 4.0 International licence (<a href="https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.en">CC BY-NC-ND 4.0</a>). See our <a href="/policy/">Policy</a> page for the full open-access terms.</li>
</ul>

<h2>5. Article Lifecycle &mdash; Corrections, Errata &amp; Retractions</h2>
<p>[[NAME]] follows standard scholarly publishing practice for maintaining the integrity of the published record.</p>
<table>
<thead><tr><th scope="col">Event</th><th scope="col">Mechanism</th></tr></thead>
<tbody>
<tr><td>Minor typographical or factual error</td><td>Erratum published as a separate notice linked to the original article; original is preserved unchanged.</td></tr>
<tr><td>Significant error, main findings unaffected</td><td>Correction notice published; article may be updated with a dated change log appended to the end.</td></tr>
<tr><td>Fundamental flaw undermining findings</td><td>Retraction notice published; article preserved with a RETRACTED watermark and cross-link to the notice.</td></tr>
<tr><td>Legal or serious ethical violation</td><td>Decided by the editorial team; body text may be removed in exceptional cases with a permanent public notice replacing it.</td></tr>
<tr><td>Author requests post-publication change</td><td>Reviewed by the editors; only substantive corrections accepted. Contact <a href="mailto:[[EMAIL]]">[[EMAIL]]</a>.</td></tr>
</tbody>
</table>
<p><strong>Authors cannot unilaterally delete or modify published articles.</strong> Before acceptance, authors may withdraw a submission through the editorial workflow. After publication, changes must go through the above process. This is necessary because published articles enter the scholarly citation record; DOI registration makes them permanently resolvable, and silent deletion would break citation chains.</p>

<h2>6. Withdrawal Before Publication</h2>
<p>Authors may request withdrawal of a submitted manuscript at any stage prior to acceptance. After acceptance but before formal publication, withdrawal requires editorial approval and may not be possible if the article is already in production. Requests should be made promptly by email to <a href="mailto:[[EMAIL]]">[[EMAIL]]</a>.</p>

<h2>7. Account &amp; Profile Deletion</h2>
<p>Your right to erasure (GDPR Art. 17) applies, subject to the following distinctions:</p>
<p><strong>Authors without published articles</strong> may request full account deletion. All personal data (email, name, biography, photo, institution, ORCID) is permanently removed from the platform.</p>
<p><strong>Authors with published articles</strong> &mdash; the scholarly publication record cannot be erased, because the public interest in maintaining an accurate citation record constitutes a lawful exception under GDPR Art. 17(3)(d). What we will do upon a deletion request:</p>
<ul>
<li>Remove all contact data (email, biography, photo, ORCID) from the live platform.</li>
<li>Deactivate the account (login is no longer possible).</li>
<li>Retain the authorship name on published article pages only, as originally submitted and as part of the scholarly record.</li>
<li>The author profile page will no longer be accessible.</li>
</ul>
<p><strong>Name correction</strong> &mdash; if your legal name has changed, you may request that the displayed name on your published articles be updated to reflect this. Requests are reviewed by the editorial team. Contact <a href="mailto:[[EMAIL]]">[[EMAIL]]</a>.</p>

<h2>8. Third-Party Services</h2>
<p>[[NAME]] uses the following third-party services (sub-processors) that may process personal data on our behalf:</p>
<ul>
<li><strong>Hosting provider</strong> &mdash; server infrastructure and file storage.</li>
<li><strong>Email delivery</strong> &mdash; transactional email (submission notifications, editorial correspondence).</li>
<li><strong>ORCID</strong> &mdash; optional researcher identifier. Linked only with your consent via OAuth. ORCID&rsquo;s privacy policy applies to data held on their platform.</li>
<li><strong>Crossref</strong> &mdash; DOI registration and metadata indexing. Article metadata (title, author name, abstract, publication date) is deposited with Crossref to generate a permanent DOI and enable citation indexing.</li>
<li><strong>Turnitin</strong> &mdash; manuscript similarity checking. Uploaded manuscripts are transmitted to Turnitin&rsquo;s servers for analysis. Turnitin&rsquo;s own terms and privacy policy apply.</li>
</ul>
<p>We select sub-processors that provide adequate data protection guarantees. Data is not transferred outside the EEA without appropriate safeguards (Standard Contractual Clauses or equivalent).</p>

<h2>9. Cookies</h2>
<p>This platform uses session cookies strictly necessary for login and CSRF protection. No tracking cookies or third-party advertising cookies are used. No consent banner is shown because no non-essential cookies are set.</p>

<h2>10. Changes to These Terms</h2>
<p>We may update these Terms and Conditions when there are changes to applicable law, platform features, or data practices. Material changes will be notified by email to registered users and announced on the platform. Continued use of the platform after notification constitutes acceptance of the updated terms.</p>

<h2>11. Contact</h2>
<p>For all data protection enquiries, rights requests, or questions about these terms:</p>
<p><strong>[[NAME]]</strong><br>[[INSTITUTION]][[COUNTRY]]<a href="mailto:[[EMAIL]]">[[EMAIL]]</a></p>
""".strip()


def seed(apps, schema_editor):
    JournalConfig = apps.get_model('journal', 'JournalConfig')
    journal = JournalConfig.objects.first()
    if journal is None:
        return

    name = journal.name or 'InAct'
    email = journal.editorial_email or 'editorial@in-act-journal.org'
    institution = (journal.institution + '<br>') if journal.institution else ''
    country = (journal.country + '<br>') if journal.country else ''

    changed = False
    if not journal.policy_text:
        journal.policy_text = POLICY_HTML
        changed = True
    if not journal.terms_text:
        journal.terms_text = (
            TERMS_HTML
            .replace('[[NAME]]', name)
            .replace('[[EMAIL]]', email)
            .replace('[[INSTITUTION]]', institution)
            .replace('[[COUNTRY]]', country)
        )
        changed = True
    if changed:
        journal.save()


def unseed(apps, schema_editor):
    # Non-destructive reverse: leave content in place.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0009_journalconfig_policy_text_journalconfig_terms_text'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
