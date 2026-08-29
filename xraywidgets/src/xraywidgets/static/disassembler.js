// The front end for the disassembler.
//
// There is nothing here beyond what every widget does, because a disassembler is a picture
// with a box you type in and four buttons, and both of those are handled in `_common.js`
// above. The file exists anyway: each widget owns its module, and the day this one needs
// something of its own it has somewhere to put it.
//
// What is deliberately absent is any idea of what a disassembly means. No opcode names, no
// cache arithmetic, no exception table. Python computed all of it and sent the finished
// markup over. See xraywidgets/README.md for why that matters more than it looks.

export default {
  render({ model, el }) {
    return mount(model, el, "disassembler");
  },
};
