// The front end for the disassembler widget.
//
// This file draws nothing and decides nothing. Python sends over a `view` object with the
// finished markup in it, this puts the markup on the page, and it listens for the two things
// a reader can do: type in the source box and press a toggle. Both of those write a trait,
// Python recomputes, and a new `view` comes back.
//
// It is written this way on purpose. The moment the browser starts working out which opcodes
// are specialized, there are two answers to that question in the repository, and the one in
// JavaScript is the one nobody tests. Keeping the logic on one side means the widget you can
// click and the picture in a rendered notebook are the same picture.

// How long to wait after the last keystroke before asking Python for a new disassembly.
// Long enough that typing a word does not send a message per letter, short enough that it
// still feels like the table is following you.
const SETTLE_MS = 250;

function render(root, model) {
  const view = model.get("view") || {};
  root.innerHTML = view.html || "";
  wireSource(root, model);
  wireToggles(root, model);
}

function wireSource(root, model) {
  const box = root.querySelector('[data-role="code"]');
  if (!box) return;

  let timer = null;
  box.addEventListener("input", () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      model.set("code", box.value);
      model.save_changes();
    }, SETTLE_MS);
  });

  // Tab indents rather than leaving the box. Python is indented, and a reader who wants to
  // type a two line function should not have to hunt for the space bar four times.
  box.addEventListener("keydown", (event) => {
    if (event.key !== "Tab" || event.shiftKey) return;
    event.preventDefault();
    const at = box.selectionStart;
    box.value = box.value.slice(0, at) + "    " + box.value.slice(box.selectionEnd);
    box.selectionStart = box.selectionEnd = at + 4;
    box.dispatchEvent(new Event("input"));
  });
}

function wireToggles(root, model) {
  for (const button of root.querySelectorAll("[data-flag]")) {
    button.addEventListener("click", () => {
      const flag = button.dataset.flag;
      model.set(flag, !model.get(flag));
      model.save_changes();
    });
  }
}

export default {
  render({ model, el }) {
    const root = document.createElement("div");
    root.className = "xw";
    root.dataset.widget = "disassembler";
    el.appendChild(root);

    render(root, model);

    // Only the view is watched. The traits the buttons write are watched by Python, which
    // sends back a new view, so redrawing on both would draw twice for one click.
    // Replacing the markup throws the caret away, so where it was is saved first and put
    // back after. Without this, a box that sends you to the end of the line a quarter of a
    // second after you stop typing is unusable for anything longer than one line.
    const redraw = () => {
      const active = document.activeElement;
      const typing = active && active.dataset && active.dataset.role === "code";
      const caret = typing ? active.selectionStart : null;
      render(root, model);
      if (caret === null) return;
      const box = root.querySelector('[data-role="code"]');
      if (!box) return;
      box.focus();
      box.selectionStart = box.selectionEnd = Math.min(caret, box.value.length);
    };
    model.on("change:view", redraw);
    return () => model.off("change:view", redraw);
  },
};
