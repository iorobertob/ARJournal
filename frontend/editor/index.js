import { Editor } from '@tiptap/core';
import Document from '@tiptap/extension-document';
import Paragraph from '@tiptap/extension-paragraph';
import Text from '@tiptap/extension-text';
import Bold from '@tiptap/extension-bold';
import Italic from '@tiptap/extension-italic';
import Code from '@tiptap/extension-code';
import Heading from '@tiptap/extension-heading';
import Blockquote from '@tiptap/extension-blockquote';
import BulletList from '@tiptap/extension-bullet-list';
import OrderedList from '@tiptap/extension-ordered-list';
import ListItem from '@tiptap/extension-list-item';
import Link from '@tiptap/extension-link';
import HardBreak from '@tiptap/extension-hard-break';
import History from '@tiptap/extension-history';
import HorizontalRule from '@tiptap/extension-horizontal-rule';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';

import { FootnoteRef } from './extensions/FootnoteRef.js';
import { FigureBlock } from './extensions/FigureBlock.js';
import { MediaBlock } from './extensions/MediaBlock.js';
import { EquationBlock } from './extensions/EquationBlock.js';
import { CiteMark } from './extensions/CiteMark.js';
import { CrossRef } from './extensions/CrossRef.js';
import { serializeDocument } from './serializer.js';
import { deserializeDocument } from './deserializer.js';

// ── State ────────────────────────────────────────────────────────────────────

let editor = null;
let bibliography = [];       // array of citation item objects
let saveTimer = null;
let footnoteCounter = 0;
let saveUrl = null;
let assetUploadUrl = null;
let bibtexImportUrl = null;
let csrfToken = null;
let editingCitationIdx = null; // null = new entry, number = editing existing
let _wrapperDefaultParent = null;
let _wrapperDefaultNextSibling = null;
let bibFilterQuery = '';       // live search filter for the References list

// ── Utilities ────────────────────────────────────────────────────────────────

function debounce(fn, ms) {
  return (...args) => {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => fn(...args), ms);
  };
}

function getWysiwygPayload() {
  const doc = editor.getJSON();
  return {
    content: serializeDocument(doc),
    bibliography,
  };
}

async function autosave() {
  if (!saveUrl) return;
  const payload = getWysiwygPayload();
  try {
    await fetch(saveUrl, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(payload),
    });
    setStatusMsg('Saved');
  } catch {
    setStatusMsg('Save failed');
  }
}

function setStatusMsg(msg) {
  const el = document.getElementById('editor-status');
  if (el) { el.textContent = msg; el.dataset.status = msg === 'Saved' ? 'ok' : 'warn'; }
}

// ── Bibliography helpers ──────────────────────────────────────────────────────

// Does a citation match the live search query? Matches across key, title,
// authors, year, and container (journal/publisher) so any of them can be typed.
function bibItemMatchesQuery(item, q) {
  if (!q) return true;
  const haystack = [
    item.citeKey, item.title, item.year, item.type,
    item.journal, item.publisher, item.booktitle,
    ...(item.authors || []),
  ].filter(Boolean).join(' ').toLowerCase();
  return haystack.includes(q);
}

function renderBibliography() {
  const list = document.getElementById('bib-list');
  if (!list) return;
  const wrapper = document.getElementById('manual-cite-form-wrapper');

  // Detach the form wrapper before clearing innerHTML to prevent it being destroyed.
  // It lives inside a .bib-item-inline-form <li> when an edit is in progress.
  const inlineLi = list.querySelector('.bib-item-inline-form');
  if (inlineLi) {
    inlineLi.removeChild(wrapper);
    list.removeChild(inlineLi);
  }

  list.innerHTML = '';

  // Only expose the search field once there is something to search.
  const searchWrap = document.getElementById('bib-search-wrap');
  if (searchWrap) searchWrap.hidden = bibliography.length === 0;

  const q = bibFilterQuery.trim().toLowerCase();
  let shown = 0;

  bibliography.forEach((item, idx) => {
    // Keep the item being edited visible regardless of the filter, so an
    // in-progress inline edit is never hidden mid-type.
    const matches = editingCitationIdx === idx || bibItemMatchesQuery(item, q);
    if (!matches) return;
    shown += 1;

    const li = document.createElement('li');
    li.className = 'bib-item';
    const authorYear = [(item.authors || []).join(', '), item.year].filter(Boolean).join(' · ');
    li.innerHTML = `
      <span class="bib-item__key">[${item.citeKey}]</span>
      <button type="button" class="bib-item__cite-btn" data-idx="${idx}">Cite</button>
      <button type="button" class="bib-item__del-btn" data-idx="${idx}">×</button>
      <span class="bib-item__title">${item.title || ''}</span>
      <span class="bib-item__meta">${authorYear}</span>
      <button type="button" class="bib-item__edit-btn" data-idx="${idx}">Edit</button>
    `;
    list.appendChild(li);

    // Inline form: appears directly below the card being edited
    if (editingCitationIdx === idx && wrapper) {
      const formLi = document.createElement('li');
      formLi.className = 'bib-item-inline-form';
      formLi.appendChild(wrapper);
      list.appendChild(formLi);
    }
  });

  // Empty state when a filter excludes every reference.
  if (q && shown === 0 && bibliography.length > 0) {
    const li = document.createElement('li');
    li.className = 'bib-empty';
    li.textContent = 'No references match your search.';
    list.appendChild(li);
  }

  // Not editing: restore wrapper to its original DOM position (above the bib-list)
  if (editingCitationIdx === null && wrapper && _wrapperDefaultParent) {
    _wrapperDefaultParent.insertBefore(wrapper, _wrapperDefaultNextSibling);
  }
}

function insertCitation(item) {
  const label = item.authors?.length
    ? `${item.authors[0].split(',')[0]} ${item.year || ''}`
    : item.citeKey;
  editor.chain().focus()
    .setMark('cite', { ref: item.citeKey, label })
    .insertContent(label)
    .unsetMark('cite')
    .run();
}

function addBibItem(item) {
  if (!bibliography.find(b => b.citeKey === item.citeKey)) {
    bibliography.push(item);
    renderBibliography();
    autosave();
  }
}

function editCitation(idx) {
  const item = bibliography[idx];
  if (!item) return;
  editingCitationIdx = idx;

  document.getElementById('cite-key').value = item.citeKey || '';
  document.getElementById('cite-type').value = item.type || 'article';
  document.getElementById('cite-title').value = item.title || '';
  document.getElementById('cite-authors').value = (item.authors || []).join('; ');
  document.getElementById('cite-year').value = item.year || '';
  document.getElementById('cite-volume').value = item.volume || '';
  document.getElementById('cite-journal').value = item.journal || '';
  document.getElementById('cite-publisher').value = item.publisher || '';
  document.getElementById('cite-pages').value = item.pages || '';
  document.getElementById('cite-doi').value = item.doi || '';
  document.getElementById('cite-url').value = item.url || '';

  const submitBtn = document.getElementById('manual-cite-submit');
  if (submitBtn) submitBtn.textContent = 'Update reference';

  // Re-render places the form inline directly below the target card
  renderBibliography();
  const wrapper = document.getElementById('manual-cite-form-wrapper');
  if (wrapper) wrapper.hidden = false;
}

// ── Footnote helpers ──────────────────────────────────────────────────────────

function insertFootnote() {
  footnoteCounter += 1;
  const footnoteId = `blk_fn_${String(footnoteCounter).padStart(3, '0')}`;
  editor.chain().focus().insertContent({
    type: 'footnoteRef',
    attrs: { footnoteId, number: footnoteCounter, noteText: '' },
  }).run();

  openFootnotePopover(footnoteId, footnoteCounter, '');
}

function openFootnotePopover(footnoteId, number, noteText) {
  const popover = document.getElementById('fn-popover');
  if (!popover) return;
  popover.dataset.footnoteId = footnoteId;
  document.getElementById('fn-popover-text').value = noteText;
  document.getElementById('fn-popover-num').textContent = `Footnote ${number}`;
  popover.hidden = false;
  document.getElementById('fn-popover-text').focus();
}

function saveFootnotePopover() {
  const popover = document.getElementById('fn-popover');
  const footnoteId = popover.dataset.footnoteId;
  const noteText = document.getElementById('fn-popover-text').value;
  popover.hidden = true;

  // Update the footnoteRef node attrs
  editor.view.state.doc.descendants((node, pos) => {
    if (node.type.name === 'footnoteRef' && node.attrs.footnoteId === footnoteId) {
      editor.view.dispatch(
        editor.view.state.tr.setNodeMarkup(pos, null, { ...node.attrs, noteText })
      );
    }
  });
}

// ── Cross-reference picker ────────────────────────────────────────────────────

function openCrossRefPicker() {
  const items = [];
  editor.view.state.doc.descendants(node => {
    if (node.type.name === 'figureBlock' && node.attrs.label) {
      items.push({ target: node.attrs.label, desc: `Figure: ${node.attrs.caption || node.attrs.label}` });
    }
    if (node.type.name === 'mediaBlock' && node.attrs.label) {
      items.push({ target: node.attrs.label, desc: `${node.attrs.mediaType}: ${node.attrs.caption || node.attrs.label}` });
    }
    if (node.type.name === 'table') {
      // Tables don't have a label attr in TipTap's table ext, skip for now
    }
  });

  const picker = document.getElementById('crossref-picker');
  const list = document.getElementById('crossref-list');
  if (!picker || !list) return;
  list.innerHTML = '';
  if (!items.length) {
    list.innerHTML = '<li class="crossref-empty">No labeled figures or media yet.</li>';
  } else {
    items.forEach(item => {
      const li = document.createElement('li');
      li.className = 'crossref-item';
      li.innerHTML = `<button type="button" data-target="${item.target}">${item.desc} <code>${item.target}</code></button>`;
      list.appendChild(li);
    });
  }
  picker.hidden = false;
}

// ── Asset upload (figure / media) ─────────────────────────────────────────────

async function handleAssetUpload(file, mediaType) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('media_type', mediaType);
  const resp = await fetch(assetUploadUrl, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    body: formData,
  });
  if (!resp.ok) throw new Error('Upload failed');
  return await resp.json();
}

function openMediaModal(mediaType) {
  const modal = document.getElementById('media-upload-modal');
  if (!modal) return;
  modal.dataset.mediaType = mediaType;
  const titles = { image: 'Insert Figure', video: 'Insert Video', audio: 'Insert Audio' };
  const titleEl = document.getElementById('media-modal-title');
  if (titleEl) titleEl.textContent = titles[mediaType] || 'Insert Media';
  const altGroup = document.getElementById('alt-text-group');
  if (altGroup) altGroup.hidden = mediaType !== 'image';
  document.getElementById('media-upload-file').value = '';
  document.getElementById('media-upload-caption').value = '';
  document.getElementById('media-upload-alt').value = '';
  document.getElementById('media-upload-label').value = '';
  modal.hidden = false;
}

async function submitMediaModal() {
  const modal = document.getElementById('media-upload-modal');
  const mediaType = modal.dataset.mediaType;
  const fileInput = document.getElementById('media-upload-file');
  const file = fileInput.files[0];
  if (!file) return;

  const caption = document.getElementById('media-upload-caption').value;
  const altText = document.getElementById('media-upload-alt').value;
  const label = document.getElementById('media-upload-label').value;

  try {
    document.getElementById('media-upload-submit').disabled = true;
    const asset = await handleAssetUpload(file, mediaType);
    modal.hidden = true;

    if (mediaType === 'image') {
      editor.chain().focus().insertContent({
        type: 'figureBlock',
        attrs: {
          assetRef: asset.asset_id,
          assetUrl: asset.url,
          caption,
          altText,
          credit: '',
          label: label || asset.asset_id,
          originalFilename: asset.original_filename,
        },
      }).run();
    } else {
      editor.chain().focus().insertContent({
        type: 'mediaBlock',
        attrs: {
          mediaType,
          assetRef: asset.asset_id,
          assetUrl: asset.url,
          caption,
          label: label || asset.asset_id,
          originalFilename: asset.original_filename,
        },
      }).run();
    }
  } finally {
    document.getElementById('media-upload-submit').disabled = false;
  }
}

// ── Equation dialog ───────────────────────────────────────────────────────────

function openEquationDialog(existingLatex = '') {
  const dialog = document.getElementById('equation-dialog');
  if (!dialog) return;
  document.getElementById('equation-input').value = existingLatex;
  dialog.hidden = false;
  document.getElementById('equation-input').focus();
  updateEquationPreview();
}

function updateEquationPreview() {
  const latex = document.getElementById('equation-input').value;
  const preview = document.getElementById('equation-preview');
  if (!preview) return;
  preview.textContent = latex ? `\\(${latex}\\)` : 'Preview will appear here';
  if (window.MathJax) window.MathJax.typesetPromise([preview]).catch(() => {});
}

function insertEquationFromDialog() {
  const dialog = document.getElementById('equation-dialog');
  const latex = document.getElementById('equation-input').value;
  dialog.hidden = true;
  if (!latex.trim()) return;
  editor.chain().focus().insertContent({ type: 'equationBlock', attrs: { latex } }).run();
}

// ── BibTeX import ─────────────────────────────────────────────────────────────

async function importBibtex(file) {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(bibtexImportUrl, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    body: formData,
  });
  if (!resp.ok) throw new Error('BibTeX import failed');
  const data = await resp.json();
  (data.items || []).forEach(addBibItem);
}

// ── Manual citation form ──────────────────────────────────────────────────────

function resetCiteForm() {
  document.querySelectorAll('#manual-cite-form-wrapper input, #manual-cite-form-wrapper select')
    .forEach(el => {
      if (el.tagName === 'SELECT') el.selectedIndex = 0;
      else el.value = '';
    });
}

function submitManualCitation() {
  const citeKey = document.getElementById('cite-key').value.trim();
  if (!citeKey) return;

  const item = {
    citeKey,
    type: document.getElementById('cite-type').value,
    title: document.getElementById('cite-title').value,
    authors: document.getElementById('cite-authors').value.split(';').map(s => s.trim()).filter(Boolean),
    year: document.getElementById('cite-year').value,
    journal: document.getElementById('cite-journal').value,
    volume: document.getElementById('cite-volume').value,
    pages: document.getElementById('cite-pages').value,
    publisher: document.getElementById('cite-publisher').value,
    doi: document.getElementById('cite-doi').value,
    url: document.getElementById('cite-url').value,
  };

  if (editingCitationIdx !== null) {
    bibliography[editingCitationIdx] = item;
    editingCitationIdx = null;
  } else if (!bibliography.find(b => b.citeKey === citeKey)) {
    bibliography.push(item);
  }

  renderBibliography();
  autosave();
  resetCiteForm();
  document.getElementById('manual-cite-form-wrapper').hidden = true;
  const submitBtn = document.getElementById('manual-cite-submit');
  if (submitBtn) submitBtn.textContent = 'Add to bibliography';
}

// ── Table insertion ───────────────────────────────────────────────────────────

function insertTable(rows, cols) {
  editor.chain().focus().insertTable({ rows, cols, withHeaderRow: true }).run();
}

// ── Toolbar command dispatch ──────────────────────────────────────────────────

function bindToolbar() {
  document.getElementById('toolbar')?.addEventListener('click', e => {
    const btn = e.target.closest('[data-cmd]');
    if (!btn) return;
    const cmd = btn.dataset.cmd;

    switch (cmd) {
      case 'bold': editor.chain().focus().toggleBold().run(); break;
      case 'italic': editor.chain().focus().toggleItalic().run(); break;
      case 'h2': editor.chain().focus().toggleHeading({ level: 2 }).run(); break;
      case 'h3': editor.chain().focus().toggleHeading({ level: 3 }).run(); break;
      case 'h4': editor.chain().focus().toggleHeading({ level: 4 }).run(); break;
      case 'blockquote': editor.chain().focus().toggleBlockquote().run(); break;
      case 'bulletList': editor.chain().focus().toggleBulletList().run(); break;
      case 'orderedList': editor.chain().focus().toggleOrderedList().run(); break;
      case 'footnote': insertFootnote(); break;
      case 'equation': openEquationDialog(); break;
      case 'image': openMediaModal('image'); break;
      case 'video': openMediaModal('video'); break;
      case 'audio': openMediaModal('audio'); break;
      case 'table': insertTable(3, 3); break;
      case 'crossref': openCrossRefPicker(); break;
      case 'undo': editor.chain().focus().undo().run(); break;
      case 'redo': editor.chain().focus().redo().run(); break;
    }
  });
}

// ── Event wiring ─────────────────────────────────────────────────────────────

function bindEvents() {
  // Footnote popover
  document.getElementById('fn-popover-save')?.addEventListener('click', saveFootnotePopover);
  document.getElementById('fn-popover-cancel')?.addEventListener('click', () => {
    document.getElementById('fn-popover').hidden = true;
  });

  // Cross-ref picker
  document.getElementById('crossref-list')?.addEventListener('click', e => {
    const btn = e.target.closest('[data-target]');
    if (!btn) return;
    document.getElementById('crossref-picker').hidden = true;
    editor.chain().focus().insertContent({ type: 'crossRef', attrs: { target: btn.dataset.target } }).run();
  });
  document.getElementById('crossref-picker-close')?.addEventListener('click', () => {
    document.getElementById('crossref-picker').hidden = true;
  });

  // Media upload modal
  document.getElementById('media-upload-submit')?.addEventListener('click', submitMediaModal);
  document.getElementById('media-upload-cancel')?.addEventListener('click', () => {
    document.getElementById('media-upload-modal').hidden = true;
  });

  // Equation dialog
  document.getElementById('equation-input')?.addEventListener('input', updateEquationPreview);
  document.getElementById('equation-insert')?.addEventListener('click', insertEquationFromDialog);
  document.getElementById('equation-cancel')?.addEventListener('click', () => {
    document.getElementById('equation-dialog').hidden = true;
  });

  // Bibliography: cite / edit / delete buttons
  document.getElementById('bib-list')?.addEventListener('click', e => {
    const citeBtn = e.target.closest('.bib-item__cite-btn');
    const delBtn  = e.target.closest('.bib-item__del-btn');
    const editBtn = e.target.closest('.bib-item__edit-btn');
    if (citeBtn) insertCitation(bibliography[+citeBtn.dataset.idx]);
    if (delBtn) {
      bibliography.splice(+delBtn.dataset.idx, 1);
      renderBibliography();
      autosave();
    }
    if (editBtn) editCitation(+editBtn.dataset.idx);
  });

  // Bibliography live search — filters the References list as the user types
  document.getElementById('bib-search')?.addEventListener('input', e => {
    bibFilterQuery = e.target.value;
    renderBibliography();
  });

  // Manual citation form toggle — reset edit state when opened fresh
  document.getElementById('add-citation-btn')?.addEventListener('click', () => {
    const wrapper = document.getElementById('manual-cite-form-wrapper');
    if (!wrapper.hidden) {
      wrapper.hidden = true;
      editingCitationIdx = null;
      renderBibliography(); // restores wrapper to default position if it was inline
      const submitBtn = document.getElementById('manual-cite-submit');
      if (submitBtn) submitBtn.textContent = 'Add to bibliography';
    } else {
      editingCitationIdx = null;
      resetCiteForm();
      renderBibliography(); // ensure wrapper is back at default position before showing
      const submitBtn = document.getElementById('manual-cite-submit');
      if (submitBtn) submitBtn.textContent = 'Add to bibliography';
      wrapper.hidden = false;
    }
  });
  document.getElementById('manual-cite-submit')?.addEventListener('click', submitManualCitation);

  // BibTeX file import
  document.getElementById('bibtex-file-input')?.addEventListener('change', async e => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      await importBibtex(file);
    } catch {
      alert('Failed to import BibTeX file.');
    }
    e.target.value = '';
  });

  // Editor events from custom node views
  editor.on('footnoteClick', ({ node }) => {
    openFootnotePopover(node.attrs.footnoteId, node.attrs.number, node.attrs.noteText);
  });
  editor.on('figureEdit', ({ node, pos }) => {
    window.dispatchEvent(new CustomEvent('editor:figureEdit', {
      detail: { attrs: { ...node.attrs }, pos },
    }));
  });
  editor.on('equationEdit', ({ node }) => {
    openEquationDialog(node.attrs.latex);
  });

  // "Continue" button — force save then submit
  document.getElementById('editor-continue')?.addEventListener('click', async () => {
    clearTimeout(saveTimer);
    await autosave();
    document.getElementById('editor-continue-form')?.submit();
  });
}

// ── Init ─────────────────────────────────────────────────────────────────────

function init(options) {
  saveUrl = options.saveUrl;
  assetUploadUrl = options.assetUploadUrl;
  bibtexImportUrl = options.bibtexImportUrl;
  csrfToken = options.csrfToken;

  const initialContent = options.initialContent
    ? deserializeDocument(options.initialContent.content)
    : null;

  // Capture the default DOM position of the form wrapper so we can restore it after inline edits
  const _w = document.getElementById('manual-cite-form-wrapper');
  if (_w) {
    _wrapperDefaultParent = _w.parentNode;
    _wrapperDefaultNextSibling = _w.nextSibling;
  }

  if (options.initialBibliography) {
    bibliography = options.initialBibliography;
    renderBibliography();
  }

  editor = new Editor({
    element: document.getElementById('editor-canvas'),
    extensions: [
      Document, Paragraph, Text, Bold, Italic, Code,
      Heading.configure({ levels: [2, 3, 4] }),
      Blockquote, BulletList, OrderedList, ListItem,
      Link.configure({ openOnClick: false }),
      HardBreak, History, HorizontalRule,
      Table.configure({ resizable: false }),
      TableRow, TableCell, TableHeader,
      FootnoteRef, FigureBlock, MediaBlock, EquationBlock, CiteMark, CrossRef,
    ],
    content: initialContent || { type: 'doc', content: [{ type: 'paragraph' }] },
    onUpdate: debounce(() => { setStatusMsg('Saving…'); autosave(); }, 1200),
  });

  bindToolbar();
  bindEvents();
}

// Expose globally for Django template
window.TransActEditor = {
  init,
  updateNodeAtPos(pos, attrs) {
    if (!editor) return;
    editor.view.dispatch(
      editor.view.state.tr.setNodeMarkup(pos, null, attrs)
    );
  },
};
