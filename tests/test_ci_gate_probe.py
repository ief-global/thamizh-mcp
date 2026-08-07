"""TEMPORARY probe — proves the required check actually blocks a red PR. Deleted immediately."""


def test_deliberately_failing_probe():
    assert False, "intentional failure: verifying ci-ok blocks the merge button"
