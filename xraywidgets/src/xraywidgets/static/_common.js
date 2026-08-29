// The part of the front end that is the same for every widget.
//
// This file is prepended to each widget's own module by `Widget.esm`, so what anywidget
// loads is one module with these definitions at the top and the widget's `export default`
// at the bottom. It is done by concatenation rather than by an import because an import
// would be a second network request from inside a notebook output cell, which works in
// Jupyter and does not reliably work everywhere else a lesson gets rendered.
//
// Nothing here knows anything about Python. It puts markup on the page, restores the caret
// afterwards, and forwards two kinds of user action back to the kernel. Every decision about
// what the markup should say was made on the Python side before this file ever saw it.

// How long to wait after the last keystroke before asking Python for a new picture. Long
// enough that typing a word does not send a message per letter, short enough that the panes
// still feel like they are following you.
const SETTLE_MS = 250;

// Put the current picture on the page and hook up whatever the reader can touch.
function paint(root, model) {
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
  // type a two line function should not have to hit the space bar four times.
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

// Where the keyboard was, so it can be put back after the markup is replaced.
//
// Replacing innerHTML throws focus and the caret away. Without this, a source box sends you
// to the end of the line a quarter of a second after you stop typing, and a toggle drops you
// back to the top of the page every time you press it, which makes the whole thing unusable
// without a mouse.
//
// The list below is the data attributes that name something a reader can put the keyboard
// on. Every widget marks its controls with one of these, so this file can find the same
// control again in markup it has never seen, without knowing what any widget is made of.
const HANDLES = ["role", "flag", "option"];

function remember(root) {
  const active = document.activeElement;
  if (!root.contains(active) || !active.dataset) return null;
  for (const name of HANDLES) {
    if (active.dataset[name] === undefined) continue;
    const caret = active.selectionStart;
    return { name, value: active.dataset[name], caret: caret === undefined ? null : caret };
  }
  return null;
}

function restore(root, saved) {
  if (!saved) return;
  const target = root.querySelector(`[data-${saved.name}="${saved.value}"]`);
  if (!target) return;
  target.focus();
  if (saved.caret === null || target.selectionStart === undefined) return;
  target.selectionStart = target.selectionEnd = Math.min(saved.caret, target.value.length);
}

// Everything a widget's `render` does, given the name of the widget.
//
// Only `view` is watched. The traits the buttons write are watched by Python, which sends a
// new view back, so redrawing on both would draw the same picture twice for one click.
function mount(model, el, slug) {
  const root = document.createElement("div");
  root.className = "xw";
  root.dataset.widget = slug;
  el.appendChild(root);

  paint(root, model);

  const redraw = () => {
    const saved = remember(root);
    paint(root, model);
    restore(root, saved);
  };
  model.on("change:view", redraw);
  return () => model.off("change:view", redraw);
}
