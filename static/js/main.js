/* Trans/Act Journal — main.js */

// ── Alpine modal store ────────────────────────────────────────
document.addEventListener('alpine:init', function () {
  Alpine.store('modal', {
    show: false,
    type: 'alert',   // 'alert' | 'confirm'
    title: '',
    message: '',
    okLabel: null,   // null → default ('Confirm' / 'OK')
    _resolve: null,

    _open(type, message, opts) {
      // opts: string (legacy title) or { title, okLabel }
      const options = typeof opts === 'object' && opts !== null ? opts : { title: opts };
      return new Promise((resolve) => {
        this.type    = type;
        this.message = message;
        this.title   = options.title   || '';
        this.okLabel = options.okLabel || null;
        this.show    = true;
        this._resolve = resolve;
      });
    },

    ok() {
      this.show = false;
      if (this._resolve) this._resolve(true);
      this._resolve = null;
    },

    cancel() {
      this.show = false;
      if (this._resolve) this._resolve(false);
      this._resolve = null;
    },
  });

  window.showAlert   = (msg, opts) => Alpine.store('modal')._open('alert',   msg, opts);
  window.showConfirm = (msg, opts) => Alpine.store('modal')._open('confirm', msg, opts);
});

// ── data-confirm interceptor — forms ─────────────────────────
// Handles <form data-confirm="…"> — intercepts the submit event.
document.addEventListener('submit', function (e) {
  const form = e.target;
  const msg = form.dataset.confirm;
  if (!msg) return;
  e.preventDefault();
  showConfirm(msg).then((ok) => {
    if (ok) form.submit();
  });
}, true);

// ── data-confirm interceptor — buttons and links ──────────────
// Handles <button data-confirm="…"> and <a data-confirm="…">.
// For submit buttons inside a form, injects a hidden input so the
// button's name/value is preserved when form.submit() is called.
document.addEventListener('click', function (e) {
  const el = e.target.closest('[data-confirm]');
  if (!el || el.tagName === 'FORM') return; // forms handled above

  const msg     = el.dataset.confirm;
  const okLabel = el.dataset.confirmOk || null;
  e.preventDefault();
  e.stopPropagation();

  showConfirm(msg, { okLabel }).then((ok) => {
    if (!ok) return;

    if ((el.tagName === 'BUTTON' || el.tagName === 'INPUT') && el.form) {
      const form = el.form;
      let hidden = null;
      if (el.name) {
        hidden = document.createElement('input');
        hidden.type  = 'hidden';
        hidden.name  = el.name;
        hidden.value = el.value || '';
        form.appendChild(hidden);
      }
      form.submit();
      // Clean up in case the page doesn't navigate (validation failure etc.)
      if (hidden) setTimeout(() => hidden.remove(), 500);
    } else if (el.tagName === 'A') {
      window.location.href = el.href;
    }
  });
}, true);

// ── Auto-dismiss Django messages ──────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.message').forEach(function (msg) {
    setTimeout(function () {
      msg.style.transition = 'opacity 0.3s';
      msg.style.opacity = '0';
      setTimeout(function () { msg.remove(); }, 300);
    }, 5000);
  });
});
