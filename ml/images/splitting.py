"""Splits an ordered list into train, validation and test, keeping neighbours together.

RDD2022 photos were taken along roads, so neighbouring files can show almost the same scene.
Splitting them one by one at random would put near-copies in both training and test data and
make the results look better than they are. Instead we cut the list into groups of consecutive
files and give each whole group to one split.
"""

import random


def assign_splits(
    count: int, val_fraction: float, test_fraction: float, seed: int, group_size: int
) -> list[str]:
    """Return 'train', 'val' or 'test' for each of the `count` positions, in order."""
    group_count = -(-count // group_size)  # ceiling division
    groups = list(range(group_count))
    random.Random(seed).shuffle(groups)

    def groups_for(fraction: float) -> int:
        wanted = round(group_count * fraction)
        return max(wanted, 1) if fraction > 0 and group_count >= 3 else wanted

    n_test, n_val = groups_for(test_fraction), groups_for(val_fraction)
    split_of_group = {}
    for position, group in enumerate(groups):
        split_of_group[group] = "test" if position < n_test else "val" if position < n_test + n_val else "train"
    return [split_of_group[index // group_size] for index in range(count)]
