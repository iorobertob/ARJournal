/* Trans/Act Journal — main.js */

// ── Alpine modal store ────────────────────────────────────────
document.addEventListener('alpine:init', function () {
  Alpine.store('modal', {
    show: false,
    type: 'alert',   // 'alert' | 'confirm'
    title: '',
    message: '',
    _resolve: null,

    _open(type, message, title) {
      return new Promise((resolve) => {
        this.type = type;
        this.message = message;
        this.title = title || '';
        this.show = true;
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

  window.showAlert   = (msg, title) => Alpine.store('modal')._open('alert',   msg, title);
  window.showConfirm = (msg, title) => Alpine.store('modal')._open('confirm', msg, title);
});

// ── data-confirm interceptor (forms and buttons) ──────────────
document.addEventListener('submit', function (e) {
  const form = e.target;
  const msg = form.dataset.confirm;
  if (!msg) return;
  e.preventDefault();
  showConfirm(msg).then((ok) => {
    if (ok) form.submit();
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
