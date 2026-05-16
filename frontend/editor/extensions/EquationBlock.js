import { Node, mergeAttributes } from '@tiptap/core';

export const EquationBlock = Node.create({
  name: 'equationBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      latex: { default: '' },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-equation]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { class: 'editor-equation', 'data-equation': '' }), `\\(${HTMLAttributes.latex}\\)`];
  },

  addNodeView() {
    return ({ node, editor }) => {
      const dom = document.createElement('div');
      dom.className = 'editor-equation';

      const preview = document.createElement('div');
      preview.className = 'editor-equation__preview';
      preview.textContent = node.attrs.latex ? `\\(${node.attrs.latex}\\)` : 'Empty equation';
      dom.appendChild(preview);

      // Trigger MathJax re-render if available
      if (node.attrs.latex && window.MathJax) {
        requestAnimationFrame(() => window.MathJax.typesetPromise([preview]).catch(() => {}));
      }

      const editBtn = document.createElement('button');
      editBtn.type = 'button';
      editBtn.className = 'editor-equation__edit-btn';
      editBtn.textContent = 'Edit equation';
      editBtn.addEventListener('click', () => {
        editor.emit('equationEdit', { node, dom });
      });
      dom.appendChild(editBtn);

      return { dom };
    };
  },
});
