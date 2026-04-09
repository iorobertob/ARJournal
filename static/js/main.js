/* Trans/Act Journal — main.js */
document.addEventListener('DOMContentLoaded', function () {
  // Auto-dismiss messages after 5 seconds
  document.querySelectorAll('.message').forEach(function (msg) {
    setTimeout(function () {
      msg.style.transition = 'opacity 0.3s';
      msg.style.opacity = '0';
      setTimeout(function () { msg.remove(); }, 300);
    }, 5000);
  });
});
