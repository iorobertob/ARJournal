/**
 * Reviewer annotation system.
 * Click on a paragraph/figure/block to open an annotation popup.
 * Annotations are saved via POST to /review/{id}/annotate/
 */
(function () {
  'use strict';

  const articleEl = document.getElementById('article-content');
  if (!articleEl) return;

  const reviewId = articleEl.dataset.reviewId;
  if (!reviewId) return;

  let activePopup = null;

  // Annotatable block types
  const ANNOTATABLE = '.article-paragraph, .article-figure, .article-media, .article-table, .article-heading';

  articleEl.addEventListener('click', function (e) {
    const block = e.target.closest(ANNOTATABLE);
    if (!block) return;

    // Close existing popup
    if (activePopup) {
      activePopup.remove();
      activePopup = null;
    }

    const blockId = block.dataset.blockId;
    if (!blockId) return;

    // Build popup
    const popup = document.createElement('div');
    popup.className = 'annotation-popup';
    popup.innerHTML = `
      <p style="font-size:0.75rem;color:#6B6B6B;margin-bottom:0.5rem;">Annotate block <code>${blockId}</code></p>
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
        const resp = await fetch(`/review/${reviewId}/annotate/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({
            block_id: blockId,
            comment: comment,
            selector_data: { type: 'block', blockId },
          }),
        });
        if (resp.ok) {
          block.classList.add('annotation-target');
          popup.remove();
          activePopup = null;
          appendAnnotationToPanel({ block_id: blockId, comment });
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
    item.innerHTML = `
      <p class="annotation-item__block">Block: ${ann.block_id}</p>
      <p class="annotation-item__comment">${ann.comment}</p>
    `;
    list.prepend(item);
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
