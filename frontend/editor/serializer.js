// Converts a TipTap document JSON object to the canonical content array.

let _blockCounter = {};

function nextId(prefix) {
  _blockCounter[prefix] = (_blockCounter[prefix] || 0) + 1;
  return `${prefix}_${String(_blockCounter[prefix]).padStart(3, '0')}`;
}

function resetCounters() {
  _blockCounter = {};
}

function serializeInline(nodes) {
  if (!nodes) return [];
  return nodes.map(n => {
    if (n.type === 'text') {
      const marks = n.marks || [];
      const bold = marks.find(m => m.type === 'bold');
      const italic = marks.find(m => m.type === 'italic');
      const code = marks.find(m => m.type === 'code');
      const link = marks.find(m => m.type === 'link');
      const cite = marks.find(m => m.type === 'cite');

      if (cite) return { type: 'cite', ref: cite.attrs.ref, keys: [cite.attrs.ref], text: n.text };
      if (link) return { type: 'link', href: link.attrs.href, text: n.text };
      if (bold) return { type: 'bold', text: n.text };
      if (italic) return { type: 'italic', text: n.text };
      if (code) return { type: 'code', text: n.text };
      return { type: 'text', text: n.text };
    }
    if (n.type === 'footnoteRef') {
      return {
        type: 'footnote_ref',
        footnoteId: n.attrs.footnoteId,
        number: n.attrs.number,
        noteText: n.attrs.noteText || '',
      };
    }
    if (n.type === 'crossRef') {
      return { type: 'ref', target: n.attrs.target };
    }
    if (n.type === 'hardBreak') {
      return { type: 'text', text: '\n' };
    }
    return { type: 'text', text: '' };
  }).filter(n => n.type !== 'text' || n.text !== '');
}

function serializeBlock(node, fnAccumulator) {
  switch (node.type) {
    case 'heading': {
      const id = nextId('blk_h');
      return {
        id,
        type: 'heading',
        level: node.attrs.level,
        text: (node.content || []).map(n => n.text || '').join(''),
        numbering: null,
        sectionId: id,
      };
    }

    case 'paragraph': {
      const id = nextId('blk_p');
      return {
        id,
        type: 'paragraph',
        content: serializeInline(node.content),
        anchor: { sectionId: id, paragraphNumber: _blockCounter['blk_p'] },
      };
    }

    case 'blockquote': {
      const id = nextId('blk_bq');
      const inner = (node.content || []).flatMap(child =>
        child.type === 'paragraph' ? serializeInline(child.content) : []
      );
      return { id, type: 'blockquote', content: inner };
    }

    case 'bulletList':
    case 'orderedList': {
      const id = nextId('blk_list');
      const items = (node.content || []).map(li => {
        const inline = (li.content || []).flatMap(p =>
          p.type === 'paragraph' ? serializeInline(p.content) : []
        );
        return inline;
      });
      return { id, type: 'list', ordered: node.type === 'orderedList', items };
    }

    case 'figureBlock': {
      const id = nextId('blk_fig');
      return {
        id,
        type: 'figure',
        assetRef: node.attrs.assetRef,
        assetUrl: node.attrs.assetUrl || '',
        caption: node.attrs.caption || '',
        altText: node.attrs.altText || '',
        credit: node.attrs.credit || '',
        label: node.attrs.label || id,
      };
    }

    case 'mediaBlock': {
      const id = nextId('blk_med');
      return {
        id,
        type: 'media',
        mediaType: node.attrs.mediaType || 'video',
        assetRef: node.attrs.assetRef,
        assetUrl: node.attrs.assetUrl || '',
        caption: node.attrs.caption || '',
        label: node.attrs.label || id,
      };
    }

    case 'equationBlock': {
      const id = nextId('blk_eq');
      return { id, type: 'equation', latex: node.attrs.latex || '' };
    }

    case 'table': {
      const id = nextId('blk_tbl');
      const rows = [];
      let columns = null;
      (node.content || []).forEach(rowNode => {
        const cells = (rowNode.content || []).map(cell => {
          const text = (cell.content || [])
            .flatMap(p => (p.content || []).map(t => t.text || ''))
            .join('');
          return { value: text };
        });
        if (!columns) columns = cells.map((_, i) => ({ label: `Column ${i + 1}` }));
        rows.push(cells);
      });
      return {
        id,
        type: 'table',
        caption: '',
        columns: columns || [],
        rows,
        label: '',
      };
    }

    default:
      return null;
  }
}

function collectFootnotes(node, accumulator) {
  if (node.type === 'footnoteRef') {
    accumulator.push({
      id: node.attrs.footnoteId,
      type: 'footnote',
      number: node.attrs.number,
      content: [{ type: 'text', text: node.attrs.noteText || '' }],
      sectionId: node.attrs.footnoteId,
    });
  }
  (node.content || []).forEach(child => collectFootnotes(child, accumulator));
}

export function serializeDocument(tiptapJson) {
  resetCounters();
  const blocks = [];
  const footnotes = [];

  for (const node of (tiptapJson.content || [])) {
    const block = serializeBlock(node, footnotes);
    if (block) blocks.push(block);
  }

  // Collect footnotes from all inline nodes
  tiptapJson.content?.forEach(n => collectFootnotes(n, footnotes));

  if (footnotes.length > 0) {
    blocks.push({
      id: 'blk_fn_section',
      type: 'footnotes_section',
      footnotes,
    });
  }

  return blocks;
}
