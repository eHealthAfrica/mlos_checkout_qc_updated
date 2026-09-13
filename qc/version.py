"""Single source of the app's shipped version, D-04.

Maintenance rule: bump the second component whenever a phase changes the shipped rule set or
the submission record's shape; bump the first component at a milestone boundary. This is the
only place in the repository the version is spelled, because a reader of an old submission
record needs to know which rule set produced it and the Space itself exposes no git sha.
"""

VERSION = "0.5.0"
