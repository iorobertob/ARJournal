import { Node, mergeAttributes } from '@tiptap/core';

export const FigureBlock = Node.create({
  name: 'figureBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      assetRef: { default: null },
      assetUrl: { default: null },
      caption: { default: '' },
      altText: { default: '' },
      credit: { default: '' },
      label: { default: '' },
      originalFilename: { default: '' },
    };
  },

  parseHTML() {
    return [{ tag: 'figure[data-asset-ref]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['figure', mergeAttributes(HTMLAttributes, { class: 'editor-figure', 'data-asset-ref': HTMLAttributes.assetRef }), 0];
  },

  addNodeView() {
    return ({ node, editor }) => {
      const dom = document.createElement('figure');
      dom.className = 'editor-figure';
      dom.setAttribute('data-asset-ref', node.attrs.assetRef || '');

      const img = document.createElement('img');
      img.src = node.attrs.assetUrl || '';
      img.alt = node.attrs.altText || '';
      img.className = 'editor-figure__img';
      dom.appendChild(img);

      const meta = document.createElement('div');
      meta.className = 'editor-figure__meta';

      const captionEl = document.createElement('figcaption');
      captionEl.textContent = node.attrs.caption || '(no caption)';
      captionEl.className = 'editor-figure__caption';
      meta.appendChild(captionEl);

      if (node.attrs.label) {
        const labelEl = document.createElement('span');
        labelEl.className = 'editor-figure__label';
        labelEl.textContent = `Label: ${node.attrs.label}`;
        meta.appendChild(labelEl);
      }

      dom.appendChild(meta);

      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'editor-figure__edit-btn';
      editBtn.textContent = 'Edit';
      editBtn.addEventListener('click', () => {
        editor.emit('figureEdit', { node, pos: editor.view.posAtDOM(dom, 0) });
      });
      dom.appendChild(editBtn);

      return { dom };
    };
  },
});
