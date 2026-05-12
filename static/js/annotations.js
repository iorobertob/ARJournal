/**
 * Reviewer annotation system.
 * Click on a paragraph/figure/block to open an annotation popup.
 * Annotations are saved via POST to /review/{id}/annotate/
 *
 * Annotation mode must be active (via the #annotate-toggle button) before
 * clicking a block does anything.
 */
(function () {
  'use strict';

  const articleEl = document.getElementById('article-content');
  if (!articleEl) return;

  const reviewId = articleEl.dataset.reviewId;
  if (!reviewId) return;

  let activePopup = null;
  let annotationMode = false;

  // ── Paragraph numbers ────────────────────────────────────────────────────
  articleEl.querySelectorAll('.article-paragraph[data-para]').forEach(function (p) {
    const num = p.dataset.para;
    if (!num) return;
    const span = document.createElement('span');
    span.className = 'para-num';
    span.setAttribute('aria-hidden', 'true');
    span.textContent = num;
    p.insertBefore(span, p.firstChild);
  });

  // ── Annotate toggle button ───────────────────────────────────────────────
  const toggleBtn = document.getElementById('annotate-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', function () {
      annotationMode = !annotationMode;
      articleEl.classList.toggle('annotation-mode', annotationMode);
      toggleBtn.textContent = annotationMode ? '✕ Stop Annotating' : '+ Annotate';
      toggleBtn.classList.toggle('btn--primary', annotationMode);
      toggleBtn.classList.toggle('btn--secondary', !annotationMode);
      if (!annotationMode && activePopup) {
        activePopup.remove();
        activePopup = null;
      }
    });
  }

  // ── Annotatable block types ──────────────────────────────────────────────
  const ANNOTATABLE = '.article-paragraph, .article-figure, .article-media, .article-table, .article-heading';

  articleEl.addEventListener('click', function (e) {
    if (!annotationMode) return;

    const block = e.target.closest(ANNOTATABLE);
    if (!block) return;

    // Close existing popup
    if (activePopup) {
      activePopup.remove();
      activePopup = null;
    }

    const blockId = block.dataset.blockId;
    if (!blockId) return;

    const paraNum = block.dataset.para || null;
    const section = findSectionHeading(block);

    let popupLabel = 'Annotate';
    if (paraNum) popupLabel += ` ¶${paraNum}`;
    if (section) popupLabel += ` · ${section}`;

    // Build popup
    const popup = document.createElement('div');
    popup.className = 'annotation-popup';
    popup.innerHTML = `
      <p style="font-size:0.75rem;color:#6B6B6B;margin-bottom:0.5rem;">${popupLabel}</p>
      <textarea rows="3" placeholder="Your annotation…"></textarea>
      <div style="display:flex;gap:0.5rem;">
        <button class="btn btn--small btn--primary" id="ann-save">Save</button>
        <button class="btn btn--small btn--ghost" id="ann-cancel">Cancel</button>
      </div>
    `;

    block.style.position = 'relative';
    block.appendChild(popup);
    activePopup = popup;
    popup.querySelector('textarea').focus();

    popup.querySelector('#ann-cancel').addEventListener('click', function () {
      popup.remove();
      activePopup = null;
    });

    popup.querySelector('#ann-save').addEventListener('click', async function () {
      const comment = popup.querySelector('textarea').value.trim();
      if (!comment) return;

      const csrfToken = getCookie('csrftoken');
      try {
        const resp = await fetch(`${SCRIPT_NAME}/review/${reviewId}/annotate/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            block_id: blockId,
            comment: comment,
            selector_data: { type: 'block', blockId, para: paraNum, section: section || null },
          }),
        });
        if (resp.ok) {
          block.classList.add('annotation-target');
          popup.remove();
          activePopup = null;
          appendAnnotationToPanel({ block_id: blockId, comment, para: paraNum, section });
        }
      } catch (err) {
        console.error('Annotation save failed:', err);
      }
    });
  });

  // Close popup on outside click
  document.addEventListener('click', function (e) {
    if (activePopup && !activePopup.contains(e.target) && !e.target.closest(ANNOTATABLE)) {
      activePopup.remove();
      activePopup = null;
    }
  });

  function appendAnnotationToPanel(ann) {
    const list = document.getElementById('annotations-list');
    if (!list) return;
    const emptyMsg = list.querySelector('p');
    if (emptyMsg) emptyMsg.remove();
    const item = document.createElement('div');
    item.className = 'annotation-item';
    item.dataset.blockId = ann.block_id;
    let label = ann.para ? `¶${ann.para}` : ann.block_id;
    if (ann.section) label += ` · ${ann.section}`;
    item.innerHTML = `
      <p class="annotation-item__block">${label}</p>
      <p class="annotation-item__comment">${ann.comment}</p>
    `;
    list.prepend(item);
  }

  function findSectionHeading(block) {
    let el = block.previousElementSibling;
    while (el) {
      if (el.classList.contains('article-heading')) {
        return el.textContent.trim().slice(0, 60);
      }
      el = el.previousElementSibling;
    }
    return null;
  }

  function getCookie(name) {
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
      const [k, v] = c.trim().split('=');
      if (k === name) return decodeURIComponent(v);
    }
    return '';
  }
})();
