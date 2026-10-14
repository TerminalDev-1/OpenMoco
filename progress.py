"""13.5.1 tutorial references evidenced by the supplied client tables.

574 updates client-home +0x118: pairs of raw tutorial/step data references.
Native 0x686754 and 0x7969a0 store a null step when a tutorial finishes.
"""
TUTORIAL_STEPS = {
    15600000: range(14200000, 14200004),
    15600001: range(14200004, 14200009),
    15600002: range(14200009, 14200014),
    15600003: range(14200014, 14200018),
    15600004: range(14200018, 14200022),
    15600005: range(14200022, 14200026),
    15600006: range(14200026, 14200027),
    15600007: range(14200027, 14200028),
    15600008: range(14200028, 14200029),
    15600009: range(14200029, 14200033),
    15600010: range(14200033, 14200034),
}


def validate_tutorial(tutorial, step):
    if type(tutorial) is not int or tutorial not in TUTORIAL_STEPS:
        raise ValueError('Unsupported tutorial reference')
    if type(step) is not int or step != 0 and step not in TUTORIAL_STEPS[tutorial]:
        raise ValueError('Step does not belong to tutorial')


def tutorial_entries(progress):
    entries = []
    for key, step in progress.items():
        tutorial = int(key)
        validate_tutorial(tutorial, step)
        entries.append((tutorial, step))
    return sorted(entries)
