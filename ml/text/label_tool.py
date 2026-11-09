"""Label complaints one at a time from the keyboard.

    python -m ml.text.label_tool --input ml/data/text/test_pool.csv --labeler ali

Your answers are saved after every complaint, so you can quit (q) and continue later.
You never see anyone else's labels.
"""

import argparse
from collections import deque
from collections.abc import Callable
from pathlib import Path

from ml.common.paths import LABELS_DIR
from ml.text.csv_io import read_rows
from ml.text.labeling import Item, LabelStore, format_menu, load_items, parse_choice

HELP = "Press 1-5 to label, s = skip for now, u = undo the last label, q = quit and save."


def run_session(
    items: list[Item],
    store: LabelStore,
    ask: Callable[[str], str] = input,
    show: Callable[[str], None] = print,
) -> int:
    """Run the labeling loop. Returns how many complaints were labeled in this session."""
    queue = deque(item for item in items if item.id not in store.labeled_ids())
    already_done = len(items) - len(queue)
    history: list[Item] = []
    show(f"{len(queue)} complaints to label. {HELP}\n")

    while queue:
        item = queue.popleft()
        position = already_done + len(history) + 1
        show(f"[{position}/{len(items)}] ({item.language})\n{item.text}\n{format_menu()}")
        answer = ask("> ").strip().lower()

        if answer == "q":
            break
        if answer == "s":
            queue.append(item)
        elif answer == "u":
            queue.appendleft(item)
            if history:
                queue.appendleft(history.pop())
                store.undo()
            else:
                show("Nothing to undo.")
        elif (label := parse_choice(answer)) is not None:
            store.add(item, label)
            history.append(item)
        else:
            show(f"Not understood. {HELP}")
            queue.appendleft(item)
        show("")

    show(f"Saved. {len(history)} labeled in this session.")
    return len(history)


def main() -> int:
    parser = argparse.ArgumentParser(description="Label complaints from the keyboard.")
    parser.add_argument("--input", type=Path, required=True, help="CSV with columns id,text,language")
    parser.add_argument("--labeler", required=True, help="Your name, e.g. ali")
    parser.add_argument("--output-dir", type=Path, default=LABELS_DIR)
    args = parser.parse_args()

    store = LabelStore(args.output_dir / f"{args.labeler}.csv", args.labeler)
    run_session(load_items(read_rows(args.input)), store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
