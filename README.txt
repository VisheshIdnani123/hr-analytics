HR Data Analytics Portfolio

Files
- HR_Data_Analytics_Weeks_1_to_4.docx: main report with methodology and required 200+ word submission description.
- hr_raw.csv: simulated source data with deliberate data quality issues and one duplicate.
- hr_clean.csv: cleaned output (300 unique employee IDs).
- hr_dashboard.html: standalone dashboard; open in a browser.
- attrition_test_scores.csv: held-out predictions from baseline logistic regression.
- generate_clean_analyze.py: reproducible pipeline (see below).

Dataset is simulated with seed 42; it is not real employee data. Synthetic attrition is generated probabilistically from overtime, satisfaction, tenure and performance.

Cleaning rules: remove duplicate employee_id, trim and title-case categories, parse ISO dates, convert salary to integer, mark invalid salary/date missing, median-impute satisfaction. No records are dropped for missing optional measurements.

Validation snapshot: 300 records, 300 unique IDs, 55 attrition=Yes (18.3%), median satisfaction imputation=3. Missing values retained: salary 3, hire date 1.

Rebuild: run `python generate_clean_analyze.py` from this directory. Uses Python standard library only.
