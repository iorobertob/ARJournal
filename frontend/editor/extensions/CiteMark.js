import { Mark, mergeAttributes } from '@tiptap/core';

export const CiteMark = Mark.create({
  name: 'cite',
  inclusive: false,

  addAttributes() {
    return {
      ref: { default: null },   // citeKey
      label: { default: '' },   // rendered label e.g. "Smith 2024"
    };
  },

  parseHTML() {
    return [{ tag: 'a[data-cite-ref]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'a',
      mergeAttributes(HTMLAttributes, {
        'data-cite-ref': HTMLAttributes.ref,
        class: 'editor-cite',
        href: '#',
      }),
      0,
    ];
  },
});
