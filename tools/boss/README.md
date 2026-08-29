# boss

The end of part boss fights, and the harness that keeps their graders honest.

A boss fight is a problem at the end of a lesson that the lesson does not solve for you. You write a file, you run the grader, and the grader either says you agree with CPython or tells you the first place you stopped. There is no answer in the text to check yourself against, which is the point: everything up to here you could have followed along with, and this is the bit where you find out whether you actually have the model.

The graders live with their lessons, at `lessons/<lesson>/grade.py`. That is deliberate. A reader should be able to clone the repository, or download that one file, and run it with whatever Python they already have, with nothing installed and nothing built. So a grader is one file, standard library only, and `boss check` fails if that ever stops being true.

## What is in here

`src/boss` is the harness. It knows which fights exist, checks each one is still assembled, and runs graders against submissions.

`submissions/<code>/good.py` is a submission that passes. `submissions/<code>/bad.py` is one that fails, and fails the way a real first attempt fails rather than by being obviously broken. `submissions/<code>/expected.txt` is the lines the grader has to say when it turns the bad one down.

The submissions are here rather than next to the lesson because `good.py` is the answer, and an answer sitting in the directory a reader has just been told to copy the starter from is an answer they will read by accident.

## Running it

```
uv run boss list                    every fight, and the command a reader runs
uv run boss check                   the checks that run nothing
uv run boss verify                  run the graders against both submissions
uv run boss verify --seeds 20       the same, over twenty different generated corpora
uv run boss grade t05 answer.py     grade a file, the way a reader does
```

`just boss` runs `check` and `verify` together, and is part of `just check`. CI runs `verify` over a wider spread of seeds in a job of its own.

## Why the bad submission exists

A grader nobody has watched fail is a grader that might be waving everything through. That failure mode is silent and it is permanent: the good submission keeps passing, the ticks stay green, and the fight stops being a fight. The only cheap defence is to hand the grader something wrong on every pull request and insist it notices, with the message it promised to give.

Checking the message rather than just the exit code matters for the same reason. A grader that says "incorrect" is technically saying no and is useless to the person reading it, and the whole value of the fight is in the sentence that names where you and CPython parted company.
