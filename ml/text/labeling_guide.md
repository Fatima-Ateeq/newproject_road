# Labeling guide for complaint text

Read this fully before labeling. Everyone follows the same rules, so our labels agree.

## The task

For each complaint, choose **one** category. Judge the **text only**. Ignore spelling, language and tone.

| Key | Category | Use it when the complaint is about |
|---|---|---|
| 1 | Road Damage | The road surface itself: potholes, cracks, sunken or broken road, sunken manhole covers, roads dug up and never repaired |
| 2 | Traffic Congestion | Too many vehicles or blocked flow with no specific fixable fault: jams, queues, parked vehicles, hawkers, buses stopping mid-road |
| 3 | Railway Crossing | Anything about a railway crossing (phatak): gate, bell, signals, signs, missing gatekeeper, long closures |
| 4 | Missing Traffic Control | Signals, signs, markings, zebra crossings or speed breakers that are missing, faded, broken or not working |
| 5 | Other | Understandable complaints outside roads and traffic: street lights, garbage, drainage, electricity wires, stray animals, noise, bus shelters |

## Tie-break rules

1. **Label the root cause.** Choose the problem whose repair would fix the complaint.
   "A pothole near the signal causes a long queue every morning" is **Road Damage**.
2. **Railway first.** If a railway crossing is the cause, label **Railway Crossing**, even when traffic piles up.
   "The phatak gate stays closed and cars queue" is **Railway Crossing**.
3. **Broken or missing equipment is Missing Traffic Control.** A signal that does not work counts as a traffic control problem.
4. **Congestion needs no single fault.** If nothing specific is broken, it is **Traffic Congestion**.
5. **Street lights, drains and wires are Other,** even when they are on a road.
6. **Several problems in one complaint:** pick the main one, usually the one mentioned first or with the most detail. If still equal, apply rule 1.
7. **Understandable but out of scope is Other. Not understandable is skipped (press s).** Do not guess.
8. **Do not discuss labels** with the other labeler until both of you have finished.

## Examples

| Complaint | Label | Why |
|---|---|---|
| Mall road par bohat bara gaddha hai, gaariyan phans rahi hain | Road Damage | A pothole |
| سڑک پر بہت بڑا گڑھا ہے | Road Damage | A pothole, written in Urdu |
| Railway phatak par signal kharab hai aur gate band nahi hota | Railway Crossing | Rule 2 |
| Shaam ko Ferozepur road par ghanton traffic jam rehta hai | Traffic Congestion | Flow problem, no single fault |
| Chowk par traffic signal kaam nahi kar raha | Missing Traffic Control | Rule 3 |
| Street lights are off on the whole stretch near the university | Other | Rule 5 |
| Big pothole near the signal causes a long queue every morning | Road Damage | Rule 1 |

## How to run the tool

From the project root (`E:\work_folder\RoadWatch_AI`), with any Python 3.11 or newer:

```powershell
python -m ml.text.label_tool --input ml/data/text/test_pool.csv --labeler yourname
```

Keys: **1 to 5** label, **s** skip for now, **u** undo the last label, **q** quit and save.
Your answers are saved after every complaint in `ml/data/text/labels/yourname.csv`. Run the same command to continue.

## After both labelers finish

```powershell
python -m ml.text.check_agreement ml/data/text/labels/ali.csv ml/data/text/labels/sara.csv
```

It prints the agreement percentage and writes `disagreements.csv`. Discuss each disagreement together, type the
agreed category in the `final_label` column (copy the exact category name), improve this guide if a rule was unclear,
then build the final test set:

```powershell
python -m ml.text.build_gold_set ml/data/text/labels/ali.csv ml/data/text/labels/sara.csv
```
