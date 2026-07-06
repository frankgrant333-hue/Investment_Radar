# This file is intentionally (almost) empty.
#
# Its presence tells Python: "the `radar/` folder is a package — you
# can import code from it." That's what lets us write, later on:
#
#     from radar.load_data import load_ideas
#     from radar.scoring   import value_score
#
# Without this __init__.py file, Python would refuse those imports
# and we'd get a "ModuleNotFoundError: No module named 'radar'".
#
# We'll add real code here only if we ever want something to run
# automatically every time `radar` is imported. For now, empty is right.
