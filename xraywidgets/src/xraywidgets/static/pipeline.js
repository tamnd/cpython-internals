// The front end for the pipeline explorer.
//
// One box to type in and six panes that follow it, which is `_common.js` above without any
// buttons. The panes are laid out by CSS grid rather than by anything here, so the same
// widget is six columns on a wide screen and one on a phone with nothing measuring the
// window.

export default {
  render({ model, el }) {
    return mount(model, el, "pipeline");
  },
};
