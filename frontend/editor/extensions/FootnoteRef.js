import { Node, mergeAttributes } from '@tiptap/core';

export const FootnoteRef = Node.create({
  name: 'footnoteRef',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      footnoteId: { default: null },
      number: { default: null },
      noteText: { default: '' },
    };
  },

  parseHTML() {
    return [{ tag: 'sup[data-footnote-id]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'sup',
      mergeAttributes(HTMLAttributes, {
        'data-footnote-id': HTMLAttributes.footnoteId,
        class: 'editor-fn-ref',
        title: HTMLAttributes.noteText,
        contenteditable: 'false',
      }),
      `${HTMLAttributes.number || '?'}`,
    ];
  },

  addNodeView() {
    return ({ node, editor }) => {
      const dom = document.createElement('sup');
      dom.className = 'editor-fn-ref';
      dom.setAttribute('data-footnote-id', node.attrs.footnoteId);
      dom.setAttribute('contenteditable', 'false');
      dom.textContent = node.attrs.number || '?';

      dom.addEventListener('click', (e) => {
        e.stopPropagation();
        editor.emit('footnoteClick', { node, dom });
      });

      return { dom };
    };
  },
});
