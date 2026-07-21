/*
 * Lightweight, dependency-free WYSIWYG for editorial-content textareas.
 *
 * Enhances every <textarea data-wysiwyg> into a contenteditable rich-text field
 * with a small formatting toolbar. The original textarea is kept in the form
 * (visually hidden) and its value is kept in sync with the editor's HTML, so the
 * normal form POST still works. The server sanitizes the HTML on save
 * (apps/journal/sanitize.py) — this script is convenience, not a trust boundary.
 */
(function () {
  'use strict';

  var TOOLBAR = [
    { cmd: 'formatBlock', val: 'P',  label: 'P',  title: 'Paragraph' },
    { cmd: 'formatBlock', val: 'H2', label: 'H2', title: 'Heading 2' },
    { cmd: 'formatBlock', val: 'H3', label: 'H3', title: 'Heading 3' },
    { sep: true },
    { cmd: 'bold',   label: '<strong>B</strong>', title: 'Bold' },
    { cmd: 'italic', label: '<em>I</em>',         title: 'Italic' },
    { sep: true },
    { cmd: 'insertUnorderedList', label: '&bull; List', title: 'Bullet list' },
    { cmd: 'insertOrderedList',   label: '1. List',     title: 'Numbered list' },
    { cmd: 'formatBlock', val: 'BLOCKQUOTE', label: '&ldquo;&rdquo;', title: 'Quote' },
    { sep: true },
    { cmd: 'createLink', label: 'Link',   title: 'Insert link' },
    { cmd: 'unlink',     label: 'Unlink', title: 'Remove link' },
    { sep: true },
    { cmd: 'removeFormat', label: 'Clear', title: 'Clear formatting' }
  ];

  var HTML_RE = /<(p|br|h[2-6]|ul|ol|li|strong|em|b|i|u|a|blockquote)\b/i;

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Convert legacy plain text (with newlines) into paragraphs for editing.
  function plainToHtml(s) {
    return s.split(/\n{2,}/).map(function (para) {
      return '<p>' + esc(para).replace(/\n/g, '<br>') + '</p>';
    }).join('');
  }

  function isBlank(html) {
    var h = html.replace(/\s|&nbsp;/g, '');
    return h === '' || h === '<p></p>' || h === '<p><br></p>' || h === '<br>';
  }

  function enhance(textarea) {
    var wrap = document.createElement('div');
    wrap.className = 'wysiwyg';

    var bar = document.createElement('div');
    bar.className = 'wysiwyg__toolbar';
    bar.setAttribute('role', 'toolbar');

    var area = document.createElement('div');
    area.className = 'wysiwyg__area';
    area.contentEditable = 'true';
    area.setAttribute('role', 'textbox');
    area.setAttribute('aria-multiline', 'true');
    if (textarea.id) { area.setAttribute('aria-labelledby', textarea.id + '_label'); }

    var val = (textarea.value || '').trim();
    area.innerHTML = val ? (HTML_RE.test(val) ? val : plainToHtml(val)) : '<p><br></p>';

    function sync() {
      textarea.value = isBlank(area.innerHTML) ? '' : area.innerHTML.trim();
    }

    function exec(item) {
      area.focus();
      if (item.cmd === 'createLink') {
        var url = window.prompt('Link URL (https://…)', 'https://');
        if (url) { document.execCommand('createLink', false, url.trim()); }
      } else if (item.cmd === 'formatBlock') {
        // Some engines want the tag wrapped in angle brackets.
        try { document.execCommand('formatBlock', false, item.val); }
        catch (e) { document.execCommand('formatBlock', false, '<' + item.val + '>'); }
      } else {
        document.execCommand(item.cmd, false, null);
      }
      sync();
    }

    TOOLBAR.forEach(function (item) {
      if (item.sep) {
        var s = document.createElement('span');
        s.className = 'wysiwyg__sep';
        bar.appendChild(s);
        return;
      }
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'wysiwyg__btn';
      b.innerHTML = item.label;
      b.title = item.title;
      b.setAttribute('aria-label', item.title);
      // Keep selection/focus in the editor when a button is pressed.
      b.addEventListener('mousedown', function (e) { e.preventDefault(); });
      b.addEventListener('click', function () { exec(item); });
      bar.appendChild(b);
    });

    area.addEventListener('input', sync);
    area.addEventListener('blur', sync);

    // Swap the textarea out for the editor, keeping the textarea in the form.
    textarea.style.display = 'none';
    textarea.parentNode.insertBefore(wrap, textarea);
    wrap.appendChild(bar);
    wrap.appendChild(area);
    wrap.appendChild(textarea);

    if (textarea.form) {
      textarea.form.addEventListener('submit', sync);
    }
    sync();
  }

  function init() {
    var nodes = document.querySelectorAll('textarea[data-wysiwyg]');
    Array.prototype.forEach.call(nodes, enhance);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
