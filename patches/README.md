# Patches applied to CPython before the images are built

Empty, and that is the intended state.

Every `.patch` in here is applied with `git apply` in sorted order inside the build image, before `configure` runs. The directory exists so that the day something genuinely has to be carried, it is one file in a place people can find rather than a fork of CPython in somebody's account that stops being maintained the week they get busy.

A patch here changes what every lesson observes, so it needs a strong reason and it needs writing down. The bar is roughly this. Working around a bug that upstream has already fixed on main, while the pin is on a release that does not have the fix yet, is fine, and the patch should be the upstream commit with its hash in the file name. Adding instrumentation the lessons need and CPython does not have is not fine, because then the material is teaching a Python nobody else can run.

If you add one, name it `NNNN-what-it-does.patch`, put the reason and a link in a comment at the top of the file, and say in the pull request how the images were confirmed to still build. The image tooling hashes this directory into the cache key, so a change in here rebuilds everything rather than pulling a stale layer.
