import { Mark, mergeAttributes } from '@tiptap/core';

export const CiteMark = Mark.create({
  name: 'cite',
  inclusive: false,

  addAttributes() {
    return {
      ref: { default: null },   // citeKey
      label: { default: '' },   // rendered label e.g. "Smith 2024"
      page: { default: '' },    // optional locator, e.g. "45" or "45–47"
    };
  },

  parseHTML() {
    return [{
      tag: 'a[data-cite-ref]',
      getAttrs: el => ({
        ref: el.getAttribute('data-cite-ref'),
        page: el.getAttribute('data-cite-page') || '',
      }),
    }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'a',
      mergeAttributes(HTMLAttributes, {
        'data-cite-ref': HTMLAttributes.ref,
        'data-cite-page': HTMLAttributes.page || null,
        class: 'editor-cite',
        href: '#',
      }),
      0,
    ];
  },
});
