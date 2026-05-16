// Converts a canonical JSON content array back to a TipTap-compatible JSON document.

function deserializeInline(nodes) {
  if (!nodes) return [];
  return nodes.map(n => {
    switch (n.type) {
      case 'text': return { type: 'text', text: n.text || '' };
      case 'bold': return { type: 'text', text: n.text || '', marks: [{ type: 'bold' }] };
      case 'italic': return { type: 'text', text: n.text || '', marks: [{ type: 'italic' }] };
      case 'code': return { type: 'text', text: n.text || '', marks: [{ type: 'code' }] };
      case 'link': return {
        type: 'text', text: n.text || n.href,
        marks: [{ type: 'link', attrs: { href: n.href } }],
      };
      case 'cite': return {
        type: 'text', text: n.text || n.ref,
        marks: [{ type: 'cite', attrs: { ref: n.ref, label: n.text || '' } }],
      };
      case 'footnote_ref': return {
        type: 'footnoteRef',
        attrs: { footnoteId: n.footnoteId, number: n.number, noteText: n.noteText || '' },
      };
      case 'ref': return {
        type: 'crossRef',
        attrs: { target: n.target },
      };
      default: return { type: 'text', text: '' };
    }
  }).filter(n => n.type !== 'text' || n.text);
}

function deserializeBlock(block) {
  switch (block.type) {
    case 'heading':
      return {
        type: 'heading',
        attrs: { level: block.level || 2 },
        content: [{ type: 'text', text: block.text || '' }],
      };

    case 'paragraph':
      return {
        type: 'paragraph',
        content: deserializeInline(block.content),
      };

    case 'blockquote':
      return {
        type: 'blockquote',
        content: [{ type: 'paragraph', content: deserializeInline(block.content) }],
      };

    case 'list': {
      const listType = block.ordered ? 'orderedList' : 'bulletList';
      return {
        type: listType,
        content: (block.items || []).map(item => ({
          type: 'listItem',
          content: [{ type: 'paragraph', content: deserializeInline(item) }],
        })),
      };
    }

    case 'figure':
      return {
        type: 'figureBlock',
        attrs: {
          assetRef: block.assetRef,
          assetUrl: block.assetUrl || block.resolvedUrl || '',
          caption: block.caption || '',
          altText: block.altText || '',
          credit: block.credit || '',
          label: block.label || '',
        },
      };

    case 'media':
      return {
        type: 'mediaBlock',
        attrs: {
          mediaType: block.mediaType || 'video',
          assetRef: block.assetRef,
          assetUrl: block.assetUrl || block.resolvedUrl || '',
          caption: block.caption || '',
          label: block.label || '',
        },
      };

    case 'equation':
      return { type: 'equationBlock', attrs: { latex: block.latex || '' } };

    case 'table': {
      const headerRow = {
        type: 'tableRow',
        content: (block.columns || []).map(col => ({
          type: 'tableHeader',
          attrs: {},
          content: [{ type: 'paragraph', content: [{ type: 'text', text: col.label || '' }] }],
        })),
      };
      const bodyRows = (block.rows || []).map(row => ({
        type: 'tableRow',
        content: row.map(cell => ({
          type: 'tableCell',
          attrs: {},
          content: [{ type: 'paragraph', content: [{ type: 'text', text: cell.value || '' }] }],
        })),
      }));
      return { type: 'table', content: [headerRow, ...bodyRows] };
    }

    case 'footnotes_section':
    case 'bibliography':
      // Footnotes are stored inline as attrs; bibliography is in the sidebar state.
      return null;

    default:
      return null;
  }
}

export function deserializeDocument(canonicalBlocks) {
  if (!canonicalBlocks) return { type: 'doc', content: [{ type: 'paragraph', content: [] }] };
  const content = canonicalBlocks
    .map(deserializeBlock)
    .filter(Boolean);
  return { type: 'doc', content: content.length ? content : [{ type: 'paragraph', content: [] }] };
}
