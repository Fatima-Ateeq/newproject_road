# ml: data and model work

Scripts for the AI side of RoadWatch AI. Milestone 4 covers the text data and the image dataset; training comes in Milestone 5.

```
ml/
├── common/        Shared pieces: category list (read from the backend enum), data paths
├── text/          Text dataset tools (see labeling_guide.md)
├── images/        RDD2022 to YOLO conversion (see below)
├── data/text/     generated_seed*.csv, collection/, collected/, test_pool.csv, labels/, processed/
└── tests/         Run with:  pytest ml   (from the project root, backend venv active)
```

## Text data pipeline

| Step | Command (from the project root) | Result |
|---|---|---|
| 1. Collect the test pool | Everyone fills `collection/Complaint_Collection_Sheet.xlsx`, saves it as CSV into `collected/`, then `python -m ml.text.merge_collected` | `test_pool.csv` with about 100 complaints |
| 2. Two people label it | `python -m ml.text.label_tool --input ml/data/text/test_pool.csv --labeler NAME` | `labels/NAME.csv` |
| 3. Check agreement | `python -m ml.text.check_agreement labels/a.csv labels/b.csv` | Percentage and `disagreements.csv` |
| 4. Build the gold test set | `python -m ml.text.build_gold_set labels/a.csv labels/b.csv` | `gold_test.csv` |
| 5. Clean and split | `python -m ml.text.preprocess` | `processed/train.csv`, `val.csv`, `test.csv` |

## Rules

- **The test pool is written and labeled by people only.** Claude's generated data (`generated_seed.csv`) is for training.
  If the test set were written or pre-labeled by an AI, the evaluation of our AI agent would look better than it really is.
- Language codes in the data: `en` (English), `roman_ur` (Roman Urdu), `ur` (Urdu script).
- The category list is defined once, in `backend/app/core/enums.py`. Never retype it here.

## Collecting the test pool

Target: **100 to 120 complaints, at least 15 for each of the 5 scenarios**, written by people.

| Who | Files | Complaints each | Total |
|---|---|---|---|
| Team members | 3 | 20 (4 per scenario) | 60 |
| Friends and family | 8 | 5 (1 per scenario) | 40 |

1. Give everyone `ml/data/text/collection/Complaint_Collection_Sheet.xlsx`. It has three sheets: how to fill, examples, and the
   sheet to fill (`Your complaints`, with drop-downs for language and scenario).
2. Everyone saves their sheet as **CSV UTF-8 (Comma delimited)** named `collected_NAME.csv`.
3. Put all CSV files into `ml/data/text/collected/` and run `python -m ml.text.merge_collected`. It assigns ids `T001`, `T002`, ...,
   removes duplicates, rejects wrong language codes with the line number, and warns if a scenario has fewer than 15 complaints.
4. Two team members label `test_pool.csv` independently (see `text/labeling_guide.md`). The third settles disagreements.

The scenario column only helps check coverage. The labeling tool never shows it.

## Training the text classifier

```powershell
python -m ml.text.preprocess          # writes ml/data/text/processed/ (not committed, rebuild any time)
python -m ml.text.train_classifier
```

It prints 5-fold cross-validated and validation scores next to the keyword baseline, then saves the model and a card
into `backend/app/ai/artifacts/`. The saved model learns from every example. The scores come from generated text, so they
show that the model learns, not how it performs on real complaints. That is measured on the human-written gold test set.

## Training the damage detector

Needs the GPU training environment (`docs/setup.md`). Run from the project root with `ml\.venv` active.

```powershell
# 1. Quick check, a few minutes: confirms the whole pipeline works
python -m ml.images.train_yolo --data E:\work_folder\datasets\rdd2022_yolo\data.yaml --epochs 1 --fraction 0.1

# 2. The real run
python -m ml.images.train_yolo --data E:\work_folder\datasets\rdd2022_yolo\data.yaml --epochs 40
```

- Starts from a small pretrained model (`yolo11n.pt`, downloaded automatically) and fine-tunes it. Nothing is trained from scratch.
- Settings suit a 6 GB card: 640 px images, batch 8, 2 loader workers. If graphics memory runs out, use `--batch 4`.
  If the loss turns to NaN, add `--no-amp`. If training hangs, use `--workers 0`.
- Runs are saved in a `runs` folder next to the dataset, outside the repository. The best weights are `weights/best.pt`.
- `summary.json` in the run folder holds precision, recall, mAP50 and mAP50-95 on the **validation** split, per class.
  Use these to compare settings. **Do not tune on the test split.**
- When you are done choosing, add `--evaluate-test` once to measure the held-out test split. That number goes in the report.
- Also check the pictures in the run folder (`val_batch0_pred.jpg`): predicted boxes should sit on real damage.

## Image data pipeline (RDD2022 to YOLO)

RDD2022 comes as Pascal VOC XML files. YOLO needs one text file per image with normalized boxes. The script
converts the countries you choose, directly from their zip files, and builds **our own** train, validation and
test split, because the official `test` folders contain images without labels.

The release is a zip that contains one zip per country (`India.zip`, `Japan.zip`, ...). Take out only the countries
you need, then point the script at the folder holding them:

```powershell
python -c "import zipfile; z = zipfile.ZipFile(r'E:\work_folder\datasets\rdd2022\raw\RDD2022_released_through_CRDDC2022.zip'); [z.extract(f'RDD2022/{c}.zip', r'E:\work_folder\datasets\rdd2022\countries') for c in ['India', 'Japan']]"

python -m ml.images.prepare_rdd2022 `
  --source E:\work_folder\datasets\rdd2022\countries\RDD2022 `
  --out-dir E:\work_folder\datasets\rdd2022_yolo `
  --countries India Japan --max-images-per-country 2000 --max-background-ratio 0.1
```

- Result: `images/` and `labels/` folders for train, val and test, a `data.yaml` for YOLO, and `summary.json`.
- The report shows images per split and boxes per class. **Check it:** every class should appear in every split.
- Classes (YOLO ids 0 to 3): D00 longitudinal crack, D10 transverse crack, D20 alligator crack, D40 pothole.
  Boxes of any other class are left out and counted in the report.
- Images with no usable box are **background images**: they help the model avoid false alarms, but too many make it
  too cautious. In the first run about 41% of the training images were background, far above the usual advice of
  10% or less, because many images only contain other RDD2022 classes (road markings and similar) that we do not
  train on. `--max-background-ratio 0.1` keeps every image with damage and trims background images **in the training
  split only**. Validation and test keep their natural mix, so false alarms still show up in the evaluation.
- **Splitting keeps neighbouring photos together** (groups of 20 consecutive files). Photos taken along one road
  can look almost identical, and splitting them one by one would put near-copies in both training and test data.
- Keep the output outside the Git repository. It is large and must not be committed.
- Use `--max-images-per-country` to keep the dataset small enough to upload for training. The output folder
  must be empty or new, so runs never mix.
- RDD2022 license: CC BY-SA 4.0. Cite: Arya et al., "RDD2022: A multi-national image dataset for automatic road
  damage detection", Geoscience Data Journal, 2024.
