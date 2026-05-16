import { Node, mergeAttributes } from '@tiptap/core';

export const CrossRef = Node.create({
  name: 'crossRef',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      target: { default: '' },  // e.g. "fig:landscape", "tab:results"
    };
  },

  parseHTML() {
    return [{ tag: 'a[data-cross-ref]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'a',
      mergeAttributes(HTMLAttributes, {
        'data-cross-ref': HTMLAttributes.target,
        class: 'editor-crossref',
        href: '#',
        contenteditable: 'false',
      }),
      `→ ${HTMLAttributes.target}`,
    ];
  },

  addNodeView() {
    return ({ node }) => {
      const dom = document.createElement('a');
      dom.className = 'editor-crossref';
      dom.setAttribute('data-cross-ref', node.attrs.target);
      dom.setAttribute('contenteditable', 'false');
      dom.href = '#';
      dom.textContent = `→ ${node.attrs.target}`;
      return { dom };
    };
  },
});
