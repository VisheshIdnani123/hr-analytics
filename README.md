# hr-analytics

A four-week HR analytics exercise covering data preparation, statistical exploration, visualization, and an introductory attrition model. The project uses **simulated employee data only**; it contains no real employee records and should not be used for employment decisions.

## Deliverables

| File | Purpose |
|---|---|
| `HR_Data_Analytics_Weeks_1_to_4.docx` | Main report: methodology, findings, caveats, recommendations, and a report submission description exceeding 200 words. |
| `hr_raw.csv` | Simulated source data with deliberate missing, malformed, inconsistent, and duplicate values. |
| `hr_clean.csv` | Cleaned data used for summaries, dashboard, and modeling. |
| `hr_dashboard.html` | Standalone dashboard. Open it in a modern web browser. |
| `attrition_test_scores.csv` | Held-out employee IDs, actual simulated outcome, predicted probability, and 0.50-threshold class. |
| `generate_clean_analyze.py` | Reproducible data generation, cleaning, analysis/modeling, and report/dashboard creation script. |

## Dataset

The fixed-seed simulation creates 300 unique employee records with age, department, location, hire date, tenure, salary, performance rating, satisfaction, overtime, and attrition. The synthetic attrition outcome is generated probabilistically using overtime, low satisfaction, short tenure, and low performance, with random variation. These relationships are built into the simulation and are not evidence of real-world causes.

## Data quality and cleaning

The raw file includes five missing satisfaction scores, three nonnumeric salaries, inconsistent category capitalization/whitespace, one impossible hire date, and one duplicate employee record. The script applies these rules:

- Remove duplicate rows by `employee_id`, keeping the first occurrence.
- Trim whitespace and standardize category capitalization.
- Parse valid dates to ISO `YYYY-MM-DD`; retain invalid dates as blank.
- Convert salary to an integer; retain invalid salary values as blank.
- Impute missing or invalid satisfaction scores with the median of valid scores (3).
- Preserve records with missing optional values rather than dropping employees.

The cleaned output contains 300 records and 300 unique employee IDs. Salary and date exceptions are retained as missing values rather than guessed.

## Reproduce the deliverables

Use Python 3.10 or newer. The report builder needs `python-docx` in addition to Python's standard library.

From this directory, run:

```bash
python generate_clean_analyze.py
```

The script uses a fixed random seed (`42`) and writes the raw and cleaned CSVs, dashboard, test scores, and Word report to the same directory as the script. If `python-docx` is not installed, install it in your environment with `python -m pip install python-docx` before running the script.

## Analysis and model notes

The dashboard summarizes headcount, attrition, salary, performance, department attrition, and overtime comparisons. Group differences are descriptive and do not establish causation.

The baseline logistic regression predicts the simulated attrition outcome from tenure, performance, satisfaction, and overtime. It uses a seeded 80/20 train/test split, scales numeric predictors using training data only, and reports probabilities and classifications at a fixed 0.50 threshold. On this small simulated holdout, the model achieved 83.3% accuracy but had 0% precision and 0% recall at that threshold: it did not identify any attrition cases. Accuracy is therefore misleading on its own, and the model should be treated as a learning example rather than a useful predictor.
