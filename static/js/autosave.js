/**
 * Review autosave — saves draft every 30 seconds.
 */
(function () {
  'use strict';

  const form = document.getElementById('review-form');
  if (!form) return;

  const reviewId = form.dataset.reviewId;
  const saveStatus = document.getElementById('save-status');
  let saveTimer = null;

  function getFormData() {
    const fd = new FormData(form);
    const data = {};
    for (const [k, v] of fd.entries()) {
      data[k] = v;
    }
    return data;
  }

  async function saveDraft() {
    if (!reviewId) return;
    const csrfToken = getCookie('csrftoken');
    try {
      const resp = await fetch(`/review/${reviewId}/draft/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(getFormData()),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (saveStatus) {
          const t = new Date(data.saved_at);
          saveStatus.textContent = `Saved ${t.toLocaleTimeString()}`;
        }
      }
    } catch (err) {
      if (saveStatus) saveStatus.textContent = 'Save failed';
    }
  }

  // Autosave interval
  setInterval(saveDraft, 30000);

  // Manual save button
  const saveBtn = document.getElementById('save-draft-btn');
  if (saveBtn) saveBtn.addEventListener('click', saveDraft);

  // Submit review button
  const submitBtn = document.getElementById('submit-review-btn');
  if (submitBtn) {
    submitBtn.addEventListener('click', async function () {
      await saveDraft();
      const csrfToken = getCookie('csrftoken');
      try {
        const resp = await fetch(`/review/${reviewId}/submit/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify(getFormData()),
        });
        const data = await resp.json();
        if (data.status === 'submitted') {
          await showAlert('Review submitted successfully. Thank you!');
          window.location.href = '/';
        } else if (data.error) {
          showAlert(data.error);
        }
      } catch (err) {
        showAlert('Submit failed. Please try again.');
      }
    });
  }

  // Track changes
  form.addEventListener('input', function () {
    clearTimeout(saveTimer);
    if (saveStatus) saveStatus.textContent = 'Unsaved changes…';
    saveTimer = setTimeout(saveDraft, 5000);
  });

  function getCookie(name) {
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
      const [k, v] = c.trim().split('=');
      if (k === name) return decodeURIComponent(v);
    }
    return '';
  }
})();
