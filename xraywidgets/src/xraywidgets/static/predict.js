// The front end for the prediction gate.
//
// This is the one widget with a job of its own, and it is the only job the browser is
// allowed to have anywhere in this package: remembering what the reader picked. That has to
// live here, because it is stored in the reader's own browser and never sent anywhere. The
// kernel is told which option was picked so it can render the explanations, and that is the
// end of it. Nothing is scored, nothing is uploaded and nothing is kept beyond this browser.
//
// The reason for the storage at all is that a lesson notebook gets re-run. A reader who
// restarts the kernel halfway through should not be asked six questions they have already
// answered, and should not have the answers to those six wiped either.

// Reading localStorage throws in a few real situations: Safari with cookies blocked, a page
// served from a file:// URL, a browser in private mode with the quota set to zero. None of
// those are worth breaking a lesson over, so both directions fail quietly and the widget
// behaves as if the reader had not answered before, which is exactly right.
function recall(key) {
  try {
    const saved = window.localStorage.getItem(key);
    return saved === null ? null : Number.parseInt(saved, 10);
  } catch {
    return null;
  }
}

function record(key, index) {
  try {
    window.localStorage.setItem(key, String(index));
  } catch {
    // Nothing to do and nothing worth saying. The gate still works for this session.
  }
}

function wireOptions(root, model) {
  const key = (model.get("view") || {}).key;
  for (const button of root.querySelectorAll("[data-option]")) {
    button.addEventListener("click", () => {
      const index = Number.parseInt(button.dataset.option, 10);
      if (key) record(key, index);
      model.set("chosen", index);
      model.save_changes();
    });
  }
}

export default {
  render({ model, el }) {
    const root = document.createElement("div");
    root.className = "xw";
    root.dataset.widget = "predict";
    el.appendChild(root);

    const draw = () => {
      const saved = remember(root);
      root.innerHTML = (model.get("view") || {}).html || "";
      wireOptions(root, model);
      restore(root, saved);
    };

    draw();

    // An answer from a previous run of this notebook. Sent to the kernel rather than drawn
    // here, so the explanations come back from the same code that would have rendered them
    // if the reader had just clicked, and there is no second version of what a revealed
    // gate looks like.
    const key = (model.get("view") || {}).key;
    const before = key ? recall(key) : null;
    if (before !== null && !Number.isNaN(before) && model.get("chosen") < 0) {
      model.set("chosen", before);
      model.save_changes();
    }

    model.on("change:view", draw);
    return () => model.off("change:view", draw);
  },
};
