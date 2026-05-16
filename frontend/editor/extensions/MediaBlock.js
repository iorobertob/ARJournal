import { Node, mergeAttributes } from '@tiptap/core';

export const MediaBlock = Node.create({
  name: 'mediaBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      mediaType: { default: 'video' }, // 'video' | 'audio'
      assetRef: { default: null },
      assetUrl: { default: null },
      posterUrl: { default: null },
      caption: { default: '' },
      label: { default: '' },
      originalFilename: { default: '' },
    };
  },

  parseHTML() {
    return [{ tag: 'figure[data-media-type]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['figure', mergeAttributes(HTMLAttributes, { class: 'editor-media', 'data-media-type': HTMLAttributes.mediaType }), 0];
  },

  addNodeView() {
    return ({ node, editor }) => {
      const dom = document.createElement('figure');
      dom.className = `editor-media editor-media--${node.attrs.mediaType}`;

      const icon = document.createElement('div');
      icon.className = 'editor-media__icon';
      icon.textContent = node.attrs.mediaType === 'video' ? '▶ Video' : '♪ Audio';
      dom.appendChild(icon);

      const filename = document.createElement('div');
      filename.className = 'editor-media__filename';
      filename.textContent = node.attrs.originalFilename || node.attrs.assetRef || '';
      dom.appendChild(filename);

      const captionEl = document.createElement('figcaption');
      captionEl.textContent = node.attrs.caption || '(no caption)';
      captionEl.className = 'editor-media__caption';
      dom.appendChild(captionEl);

      if (node.attrs.label) {
        const labelEl = document.createElement('span');
        labelEl.className = 'editor-media__label';
        labelEl.textContent = `Label: ${node.attrs.label}`;
        dom.appendChild(labelEl);
      }

      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'editor-media__edit-btn';
      editBtn.textContent = 'Edit';
      editBtn.addEventListener('click', () => {
        editor.emit('mediaEdit', { node, pos: editor.view.posAtDOM(dom, 0) });
      });
      dom.appendChild(editBtn);

      return { dom };
    };
  },
});
