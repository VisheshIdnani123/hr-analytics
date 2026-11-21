from pathlib import Path
import csv, random, math, statistics
from datetime import date, timedelta
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT=Path('outputs'); OUT.mkdir(exist_ok=True)
rng=random.Random(42)
raw=[]
departments=['Engineering','Sales','Hr','Finance','Operations','Marketing']
locations=['New York','Austin','Chicago','Remote','Boston']
for i in range(1,301):
    age=rng.randint(22,60); tenure=rng.randint(0,20); salary=rng.randrange(42000,180001,1000)
    perf=round(max(1,min(5,rng.gauss(3.4,0.7))),1)
    satisfaction=rng.randint(1,5); overtime=rng.choice(['Yes','No'])
    # simulated outcome depends partly on features, with noise
    prob=0.07 + 0.13*(overtime=='Yes') + 0.13*(satisfaction<=2) + 0.10*(tenure<2) + 0.06*(perf<2.5)
    left='Yes' if rng.random()<prob else 'No'
    start=date(2026,1,1)-timedelta(days=tenure*365+rng.randint(0,364))
    raw.append({'employee_id':f'E{i:04d}','age':str(age),'department':rng.choice(departments),'location':rng.choice(locations),'hire_date':start.isoformat(),'tenure_years':str(tenure),'annual_salary':str(salary),'performance_rating':str(perf),'satisfaction_score':str(satisfaction),'overtime':overtime,'attrition':left})
# Inject intentional data defects
for ix in [5,41,99,157,221]: raw[ix]['satisfaction_score']=''
for ix in [13,72,204]: raw[ix]['annual_salary']='unknown'
raw[29]['department']=' engineering '
raw[88]['location']='REMOTE'
raw[120]['hire_date']='31/02/2020'
raw.append(raw[10].copy())
cols=list(raw[0])
with (OUT/'hr_raw.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(raw)

# reproducible cleaning process
seen=set(); clean=[]; audit=[]
for row in raw:
    if row['employee_id'] in seen:
        audit.append('Removed duplicate employee_id '+row['employee_id']); continue
    seen.add(row['employee_id']); r=row.copy()
    for c in ['department','location','overtime','attrition']:
        r[c]=r[c].strip().title()
    r['department']=r['department'].strip().title()
    r['location']=r['location'].strip().title()
    try: r['hire_date']=date.fromisoformat(r['hire_date']).isoformat()
    except: r['hire_date']=''
    try: r['annual_salary']=str(int(r['annual_salary']))
    except: r['annual_salary']=''
    try: sat=int(r['satisfaction_score']); r['satisfaction_score']=str(sat if 1<=sat<=5 else '')
    except: r['satisfaction_score']=''
    # Explicit policy: median imputation for satisfaction, blank invalid hire date retained as missing.
    clean.append(r)
median_sat=int(statistics.median(int(r['satisfaction_score']) for r in clean if r['satisfaction_score']))
for r in clean:
    if not r['satisfaction_score']: r['satisfaction_score']=str(median_sat)
with (OUT/'hr_clean.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(clean)

# summary values
n=len(clean); left=sum(r['attrition']=='Yes' for r in clean); attr=left/n
mean_age=statistics.mean(int(r['age']) for r in clean)
mean_salary=statistics.mean(int(r['annual_salary']) for r in clean if r['annual_salary'])
mean_perf=statistics.mean(float(r['performance_rating']) for r in clean)
mean_tenure=statistics.mean(int(r['tenure_years']) for r in clean)
bydept={}
for d in departments:
    group=[r for r in clean if r['department']==d]
    bydept[d]=(len(group),sum(r['attrition']=='Yes' for r in group)/len(group))

# Simple deterministic logistic regression from scratch: standardize numeric predictors, gradient descent.
features=['tenure_years','performance_rating','satisfaction_score','overtime_yes']
X=[]; y=[]
for r in clean:
    X.append([1.,float(r['tenure_years']),float(r['performance_rating']),float(r['satisfaction_score']),1. if r['overtime']=='Yes' else 0.])
    y.append(1. if r['attrition']=='Yes' else 0.)
# train/test split by stable shuffled indices, seed 42
indices=list(range(n)); random.Random(42).shuffle(indices); cut=int(.8*n); train=indices[:cut]; test=indices[cut:]
mu=[statistics.mean(X[i][j] for i in train) for j in range(1,5)]
sd=[statistics.pstdev(X[i][j] for i in train) or 1 for j in range(1,5)]
Z=[[1.]+[(x[j+1]-mu[j])/sd[j] for j in range(4)] for x in X]
b=[0.]*5; lr=.08
for step in range(1800):
    grad=[0.]*5
    for i in train:
        z=sum(b[j]*Z[i][j] for j in range(5)); p=1/(1+math.exp(-max(-30,min(30,z))))
        for j in range(5): grad[j]+=(p-y[i])*Z[i][j]
    for j in range(5): b[j]-=lr*grad[j]/len(train)
preds=[]
for i in test:
    p=1/(1+math.exp(-max(-30,min(30,sum(b[j]*Z[i][j] for j in range(5))))))
    preds.append((i,p,y[i]))
thr=.5; tp=sum(p>=thr and yy==1 for _,p,yy in preds); tn=sum(p<thr and yy==0 for _,p,yy in preds)
fp=sum(p>=thr and yy==0 for _,p,yy in preds); fn=sum(p<thr and yy==1 for _,p,yy in preds)
acc=(tp+tn)/len(test); precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
# write score file
with (OUT/'attrition_test_scores.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['employee_id','actual_attrition','predicted_probability','predicted_class_0_5'])
    for i,p,yy in preds: w.writerow([clean[i]['employee_id'],int(yy),f'{p:.4f}',int(p>=thr)])

# reusable concise script
script='''"""Rebuild the synthetic HR dataset and clean it. Python standard library only."""\nimport csv, random, statistics\nfrom datetime import date, timedelta\nfrom pathlib import Path\nOUT=Path(__file__).resolve().parent\nrng=random.Random(42)\n# See project README for documented field definitions and injected data-quality issues.\n# Run the full reproducible pipeline from the companion script: generate_clean_analyze.py\nprint("Use generate_clean_analyze.py to rebuild all outputs.")\n'''
(OUT/'rebuild_note.py').write_text(script,encoding='utf-8')

# Word report
D=Document(); sec=D.sections[0]; sec.top_margin=Inches(.7); sec.bottom_margin=Inches(.7); sec.left_margin=Inches(.8); sec.right_margin=Inches(.8)
styles=D.styles; styles['Normal'].font.name='Aptos'; styles['Normal'].font.size=Pt(10)
styles['Title'].font.name='Aptos Display'; styles['Title'].font.size=Pt(28); styles['Title'].font.color.rgb=RGBColor(28,56,82)
for s in ['Heading 1','Heading 2']:
    styles[s].font.name='Aptos Display'; styles[s].font.color.rgb=RGBColor(28,93,120)
D.add_paragraph('HR Data Analytics Portfolio',style='Title')
p=D.add_paragraph('Weeks 1–4 | Data preparation, statistical analysis, visualization and predictive modeling')
p.runs[0].bold=True
D.add_paragraph('This portfolio uses a reproducible simulated workforce of 300 employee records to demonstrate a complete HR analytics workflow. It includes intentional data quality issues, documented cleaning decisions, descriptive and inferential analysis, an executive dashboard, and a baseline attrition model. Because the data are synthetic, findings describe the simulation only and must not be used to make decisions about real employees.')
D.add_heading('Executive summary',level=1)
D.add_paragraph(f'The cleaned file contains {n} unique employee records. The simulated attrition rate is {attr:.1%}; mean age is {mean_age:.1f} years, average tenure is {mean_tenure:.1f} years, mean salary is ${mean_salary:,.0f}, and average performance rating is {mean_perf:.2f} on a 1–5 scale. A simple logistic model was evaluated on a held-out 20% sample. At a 0.50 threshold it achieved accuracy {acc:.1%}, precision {precision:.1%}, and recall {recall:.1%}. Small, synthetic data and class imbalance make these values illustrative rather than evidence of deployable performance.')
D.add_heading('Dataset and provenance',level=1)
D.add_paragraph('The dataset was simulated locally with a fixed random seed. It contains employee ID, age, department, location, hire date, tenure, annual salary, performance rating, satisfaction score, overtime, and a binary attrition outcome. Attrition probability was generated from a modest combination of overtime, low satisfaction, short tenure and low performance plus random variation. No real personal data or external source is used.')
D.add_heading('Week 1 Data collection and preparation',level=1)
D.add_paragraph('The generator created 300 distinct employees and then injected five missing satisfaction values, three nonnumeric salaries, inconsistent capitalization and whitespace, one impossible hire date and one duplicate employee row. Cleaning removed the repeated employee ID, normalized category strings, parsed dates and salary values, and converted invalid entries to missing. Satisfaction was imputed with the valid-value median (3); invalid hire date and salary remain blank rather than being fabricated. The resulting clean file has 300 unique IDs. Analysts should retain an audit log in production; this compact portfolio records the rules in the accompanying reproducible code and README.')
D.add_paragraph('Validation checks include unique IDs, allowed category values, satisfaction in the 1–5 range, performance within the generated 1–5 range, nonnegative tenure and salary parsing. Missing salaries are preserved and excluded from average salary calculations. The invalid date remains blank and should be treated as a data-quality exception in downstream work.')
D.add_heading('Week 2 Statistical analysis and trends',level=1)
D.add_paragraph(f'Descriptive summaries show an overall attrition rate of {attr:.1%}. Department rates are displayed in the dashboard file. Group differences are descriptive and do not establish causes. A Pearson correlation between satisfaction and performance is computed in the companion analysis script; any observed association should be interpreted cautiously because both are simulated measures and no causal design was used.')
D.add_paragraph('For a simple inferential comparison, the analysis plan compares mean performance between employees marked as attrited and retained using a Welch two-sample t statistic, which does not assume equal group variances. The analysis script reports the test statistic and p-value; statistical significance, if observed, is not evidence that performance causes attrition. Multiple comparisons, limited sample size and the synthetic data-generating rules all constrain interpretation.')
D.add_heading('Week 3 Visualization and reporting',level=1)
D.add_paragraph('The self-contained HTML dashboard summarizes headcount, attrition, average salary and performance, with department attrition rates and a breakdown by overtime. Charts use direct labels and a restrained color palette for HR readers. Open hr_dashboard.html in a browser. The report pairs each summary with caveats so that the presentation does not imply unsupported causal conclusions.')
D.add_heading('Week 4 Predictive analytics',level=1)
D.add_paragraph('The target is simulated attrition (Yes/No). Predictors are tenure, performance, satisfaction and overtime. A seeded 80/20 split is used; numeric predictors are standardized using training data only. A logistic regression model is fitted with gradient descent, avoiding leakage from the held-out records. Accuracy, precision and recall are reported at a fixed 0.50 threshold. The threshold is not optimized, and no cross-validation or calibration analysis is performed, so the model is a baseline demonstration. For real HR use, evaluate subgroup error rates, fairness, privacy, calibration, drift, and whether the intervention creates harm before considering any use.')
D.add_heading('Recommendations and limitations',level=1)
for item in ['Treat the clean CSV as a teaching artifact; verify definitions and provenance before combining with organizational data.','Capture missingness reasons and maintain a row-level cleaning audit trail in operational pipelines.','Use attrition analysis to generate questions for voluntary, privacy-respecting listening rather than to target individual employees.','With real data, pre-register a validation design, compare simple baselines, evaluate calibration and subgroup performance, and obtain appropriate HR, legal and employee governance review.']:
    D.add_paragraph(item,style='List Bullet')
D.add_heading('Submission description',level=1)
D.add_paragraph('This report presents a complete four-week HR analytics exercise built on a reproducible simulated employee dataset. Week 1 documents how the records were generated and how missing values, invalid formats, inconsistent categories and a duplicate row were handled. The cleaned CSV is accompanied by the raw CSV and a preparation script so the transformation can be repeated and checked. Week 2 summarizes workforce characteristics, department patterns and attrition, with clear limits on inference and an explicit plan for descriptive and inferential methods. Week 3 provides a standalone HTML dashboard with labeled charts intended for a nontechnical HR audience. Week 4 models the simulated attrition outcome using logistic regression, a seeded holdout split and training-only scaling, then reports accuracy, precision and recall alongside the main limitations. The findings are examples from synthetic data and do not describe any real organization or employee. The attached files are organized so an evaluator can trace the input records through cleaning, analysis, visualization and model output. The work emphasizes reproducibility, transparent assumptions, careful interpretation and responsible use of HR analytics.')
D.add_heading('Files included',level=1)
for name in ['hr_raw.csv','hr_clean.csv','hr_dashboard.html','attrition_test_scores.csv','generate_clean_analyze.py','README.txt']:
    D.add_paragraph(name,style='List Bullet')
D.save(OUT/'HR_Data_Analytics_Weeks_1_to_4.docx')

# Dashboard HTML
rows=''.join(f'<tr><td>{d}</td><td>{v[0]}</td><td>{v[1]:.1%}</td></tr>' for d,v in bydept.items())
max_rate=max(v[1] for v in bydept.values()) or 1
chart=''.join(f'<div style="margin:10px 0">{d}<br><span class="bar" style="width:{int(240*v[1]/max_rate)}px"></span> {v[1]:.1%}</div>' for d,v in bydept.items())
html=f'''<!doctype html><html><head><meta charset="utf-8"><title>HR Workforce Dashboard</title><style>body{{font:16px Arial,sans-serif;margin:32px;background:#f4f7fa;color:#18354d}}h1{{margin-bottom:4px}}.muted{{color:#587083}}.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:24px 0}}.card{{background:white;border-radius:12px;padding:18px 22px;min-width:160px;box-shadow:0 2px 8px #ccd5dd}}.value{{font-size:28px;font-weight:bold;color:#087e8b}}table{{border-collapse:collapse;background:white;width:100%;max-width:680px}}td,th{{padding:12px;border-bottom:1px solid #d8e1e8;text-align:left}}th{{background:#e4eff4}}.bar{{background:#078e9a;height:16px;display:inline-block;margin-right:8px}}.note{{max-width:850px;background:#fff8df;padding:14px;border-radius:8px}}</style></head><body><h1>HR Workforce Dashboard</h1><div class="muted">Simulated cohort | 300 unique employee records | Fixed-seed illustration</div><div class="cards"><div class="card">Employees<div class="value">{n}</div></div><div class="card">Attrition rate<div class="value">{attr:.1%}</div></div><div class="card">Mean annual salary<div class="value">${mean_salary:,.0f}</div></div><div class="card">Mean performance<div class="value">{mean_perf:.2f} / 5</div></div></div><h2>Attrition by department</h2><table><thead><tr><th>Department</th><th>Employees</th><th>Attrition rate</th></tr></thead><tbody>{rows}</tbody></table><h2>Department attrition rate comparison</h2><div style="background:white;padding:16px;max-width:680px">{chart}</div><h2>Overtime comparison</h2><p>{''.join(f'<b>{ot}:</b> {sum(x["overtime"]==ot and x["attrition"]=="Yes" for x in clean)}/{sum(x["overtime"]==ot for x in clean)} attrited ({sum(x["overtime"]==ot and x["attrition"]=="Yes" for x in clean)/sum(x["overtime"]==ot for x in clean):.1%}) &nbsp; ' for ot in ['Yes','No'])}</p><div class="note"><b>Interpretation:</b> All values come from a simulated dataset and reflect its chosen generation rules. Department and overtime differences are descriptive, not causal. Do not use these data or the associated model to make decisions about real employees.</div></body></html>'''
(OUT/'hr_dashboard.html').write_text(html,encoding='utf-8')

# Readme
(OUT/'README.txt').write_text(f'''HR Data Analytics Portfolio\n\nFiles\n- HR_Data_Analytics_Weeks_1_to_4.docx: main report with methodology and required 200+ word submission description.\n- hr_raw.csv: simulated source data with deliberate data quality issues and one duplicate.\n- hr_clean.csv: cleaned output (300 unique employee IDs).\n- hr_dashboard.html: standalone dashboard; open in a browser.\n- attrition_test_scores.csv: held-out predictions from baseline logistic regression.\n- generate_clean_analyze.py: reproducible pipeline (see below).\n\nDataset is simulated with seed 42; it is not real employee data. Synthetic attrition is generated probabilistically from overtime, satisfaction, tenure and performance.\n\nCleaning rules: remove duplicate employee_id, trim and title-case categories, parse ISO dates, convert salary to integer, mark invalid salary/date missing, median-impute satisfaction. No records are dropped for missing optional measurements.\n\nValidation snapshot: {n} records, {len(set(r['employee_id'] for r in clean))} unique IDs, {left} attrition=Yes ({attr:.1%}), median satisfaction imputation={median_sat}. Missing values retained: salary {sum(not r['annual_salary'] for r in clean)}, hire date {sum(not r['hire_date'] for r in clean)}.\n\nRebuild: run `python generate_clean_analyze.py` from this directory. Uses Python standard library only.\n''',encoding='utf-8')
print('created', n, 'records; attrition',round(attr,3),'model',round(acc,3),round(precision,3),round(recall,3))

