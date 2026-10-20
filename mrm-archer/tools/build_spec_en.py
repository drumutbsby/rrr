# -*- coding: utf-8 -*-
"""English edition of the MRM Console software specification workbook (for /mrm-en).
Mirrors MRM_Konsolu_Yazilim_Tanitim.xlsx (10 sheets, same styling). Zero formulas."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

NAVY = "004A93"; RED = "E2001A"; GREY = "666666"; ZEBRA = "F5F5F5"
OUT = "/home/user/rrr/mrm-archer/MRM_Console_Software_Spec_EN.xlsx"
APP_URL = "https://drumutbsby.github.io/rrr/mrm-en/"
TR_URL = "https://drumutbsby.github.io/rrr/mrm/"
DATE = "2026-10-20"

thin = Side(style="thin", color="DDDDDD")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

def font(sz=9.5, b=False, color=None):
    return Font(name="Arial", size=sz, bold=b, color=color)

def add_table(ws, title, subtitle, headers, rows, widths, start=1, freeze=True, autofilter=True):
    r = start
    ws.cell(r, 1, title).font = font(14, True, NAVY); r += 1
    ws.cell(r, 1, subtitle).font = font(9, False, GREY); r += 1
    hdr = r
    for i, h in enumerate(headers, 1):
        c = ws.cell(hdr, i, h); c.font = font(10, True, "FFFFFF")
        c.fill = PatternFill("solid", fgColor=NAVY); c.alignment = Alignment(vertical="center", wrap_text=True); c.border = border
    r += 1
    for n, row in enumerate(rows):
        for i, v in enumerate(row, 1):
            c = ws.cell(r, i, v); c.font = font(9.5); c.alignment = Alignment(vertical="top", wrap_text=True); c.border = border
            if n % 2 == 1: c.fill = PatternFill("solid", fgColor=ZEBRA)
        r += 1
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    if freeze: ws.freeze_panes = ws.cell(hdr + 1, 1)
    if autofilter and rows: ws.auto_filter.ref = f"A{hdr}:{get_column_letter(len(headers))}{hdr + len(rows)}"
    return r

wb = Workbook()

# ------------------------------------------------------------------ data
MENUS = [
 ["dashboard","Monitoring","Overview","Model risk dashboard: KPI strip (incl. Validations In Progress + In Periodic Validation), clickable in-progress panel, tier distribution (donut), category distribution (incl. Generative AI & Agentic AI), validation calendar, recent decisions","KPI cards, donut chart, bar lists","iView / Dashboard"],
 ["risk","Monitoring","Risk Dashboard & Board","Total Model Risk Index (0-100 + appetite thresholds + trend sparkline), 5×5 heat map, unit/category breakdown, board summary","TMR index panel, conic heat map (cells clickable), print","Calculated field + iView; Report"],
 ["govern","Monitoring","Appetite & Self-Assessment","Model risk appetite indicators and the annual MRM self-assessment / attestation","Indicator list, attestation button","Questionnaire + Attestation"],
 ["bildirim","Monitoring","Notifications & Escalation","Rule-based notification engine; task generation for criticals; EMAIL NOTIFICATIONS panel (Archer Notifications request): 8 rules + outbox simulation + daily digest preview / mailto","Notification table, rule table, outbox, digest drawer","Notifications + Advanced Workflow"],
 ["envanter","MRM Applications","Model Inventory","All models bank-wide: unit×class matrix, filters (class/tier/status/unit/SOURCE), grouping, search (incl. MUID); Business Unit New Entry (declaration; MANDATORY Model Need Justification), New Model (7-section expert form: category/flags as vertical lists + Selected box, NOTA process, upstream/downstream relation panels), CSV import/export","Matrix table, filter bar, model table, model detail drawer (8 tabs), relation panels (rel-list + rel-side)","Application + Data Import"],
 ["kritiklik","MRM Applications","Criticality Assessment","Materiality (M1-M5) × Complexity (K1-K7) scoring; hard rules; result panel with Tier + apply to model","Question rows (dropdown), result panel, gauge","Questionnaire + calculated field"],
 ["aiml","MRM Applications","AI/ML Extra Assessment","Additional control set for AI/ML and GenAI models: explainability, fairness, drift, guardrails, human oversight; readiness indicator","Sectioned form, readiness score","Questionnaire (AI/ML)"],
 ["euai","MRM Applications","EU AI Act Compliance","Article-based (9-15/17/27) compliance tracker — Annex III obligations in force since 2 Aug 2026; automatic finding generation from gaps","Article table, gap→finding button","Compliance tracker + Findings"],
 ["vendor","MRM Applications","Vendor & GenAI Assurance","Third-party model governance (transparency, SLA, exit strategy, due diligence) + GenAI guardrail/red-team test log; a failed test opens a finding automatically","Vendor table+form, guardrail table+form","Sub-form records"],
 ["validasyon","MRM Applications","Model Validation","Independent validation records: type/trigger/independence, test catalog (ECB Internal Models Guide / SR 26-2), RECOMMENDATION ≠ APPROVAL separation; approval writes back to the model","Validation table, detail drawer, test catalog, form","Application + Advanced Workflow"],
 ["valplan","MRM Applications","Validation Plan","Risk-based revalidation calendar: 12-month bar chart (month clickable), overdue/upcoming list, validator capacity","Monthly calendar chart, lists, capacity bars","DATEADD calculated field + Notifications + iView"],
 ["bddk","Governance","BRSA / ICAAP Evidence","ICAAP component linkage of regulatory models; audit-ready evidence pack table; CSV + PDF output","Component table, evidence table, export","Cross-reference + Reporting"],
 ["izleme","MRM Applications","Monitoring & Metrics","Per-model metric time series (sparkline), tier-based thresholds, breach → automatic finding; measurement entry","Metric cards, sparkline SVG, measurement form","Metrics app + calculated threshold"],
 ["degisiklik","MRM Applications","Model Change","Change records (retraining/recalibration); materiality → revalidation trigger","Change table + form","Change management + workflow trigger"],
 ["pma","MRM Applications","PMA / Exceptions (IFRS9 Overlay)","IFRS9 ECL overlay governance: impact direction/amount, stage, scenario link; Model Risk Committee approval workflow; independent review","KPI strip, overlay table, approval form drawer","Sub-form + Advanced Workflow"],
 ["yasam","MRM Applications","Lifecycle","Status board (kanban) + rule-based status transitions (Draft→…→Retired)","Kanban columns, transition buttons","Advanced Workflow states"],
 ["baglanti","MRM Applications","Dependency & Impact","Model dependency network (upstream/downstream — fed by the relation panels on the New Model form, bidirectional), recursive impact analysis; Linked NOTA Process callout for the selected model","SVG network graph, impact KPIs","Cross-reference + related records"],
 ["bulgular","MRM Applications","Findings","Finding/remediation lifecycle: Open→Action Planned→In Progress→Verification (Re-test)→Pending Closure Approval→Closed; SLA (30/60/90 days); closure only by the 2nd line","KPI strip, finding table, remediation form (stepper)","Findings/Issues workflow"],
 ["yetki","Governance","Permission Matrix","Role × action matrix (three lines of defense); active role highlighted","Matrix table","Access Roles + FLS"],
 ["denetim","Governance","Audit Trail","Time-role-object record of every action (latest 200) + Content column; clicking a row opens the ACTION CONTENT drawer: field-level Previous → New value table (e.g. Validation Frequency: Annual → Biennial); clearing only by 2nd Line MRM","Log table (clickable), content drawer","History Log — field history"],
 ["feed","Governance","Data Feed / API","Archer integration simulation: feed definitions and sample payload","Feed list","Data Feed Manager / REST API"],
 ["gereklilik","Reference","Requirements Matrix","MRM requirements (A-K) → application component → regulation mapping","Reference table","—"],
 ["regulasyon","Reference","Regulation Mapping","SR 26-2 / SS1/23 / OSFI E-23 / ECB TRIM / EU AI Act / BRSA article mapping","Reference table","—"],
 ["hakkinda","Reference","About","Scope list, next enhancements, JSON backup/restore, reference frameworks (SR 26-2 supersession note)","Info cards, JSON import/export","—"],
 ["topbar","Top Bar","Role selector · Theme · Sample Data · XLSX Report · User","Active role (5 roles) switch; light/dark theme; data reset; 10-sheet XLSX report; 'Umut Okan Başbay' user chip. Note: the English edition shows a neutral 'MRM' mark instead of the Halkbank logo","Select, buttons","User session/role"],
]

UCS = [
 ["UC-01","Business Unit Model Declaration","Model Inventory","1st Line, 2nd Line MRM","—","'Business Unit New Entry' → fill the 7-section dropdown questionnaire (simple + Advanced) → Save","Model added to the inventory with status 'Pending Approval' + wf=MRM; conservative 'Medium' if no criticality given; metric series generated; Initial Validation record opened automatically","Yes"],
 ["UC-02","New Model (sectioned expert form)","Model Inventory","1st Line, 2nd Line MRM","—","'+ New Model' → 7-section form (Identity / Definition / Flags-list / NOTA / Mapping / Dates / Documentation); Category and Flags as vertical lists + 'Selected' box beside","Enters the same approval workflow as UC-01 (wf=MRM, status=Pending Approval, Initial Validation record); monitoring series generated if a metric framework is selected","Yes"],
 ["UC-03","Model Approval Workflow","Model Detail (General)","Step 1: 2nd Line MRM · Step 2: Model Risk Committee","Model waiting in wf","Model detail → Approval Workflow block → Approve/Reject","Approve: next step or Active (status=requested status); Reject: status=Draft; every decision time-role stamped","Yes"],
 ["UC-04","CSV Bulk Import","Model Inventory","1st Line, 2nd Line MRM","CSV template (downloadable via ⭳ CSV)","'⭱ Import' → choose file","Rows added as models (Pending Approval + wf=MRM); Tier computed; metric series generated. Header matching is English (model name, business unit, class, model type, category, status, metric, regulat, ai, critic, last val)","Yes"],
 ["UC-05","Inventory CSV Export","Model Inventory","All roles","—","'⭳ CSV'","halkbank_model_inventory_en.csv downloaded","Yes"],
 ["UC-06","XLSX Report","Top bar","All roles","—","'📊 XLSX Report'","10-sheet Excel workbook downloaded (Summary/Inventory/Validations/Plan/Findings/Overlay/Guardrails/Metrics/BRSA/Audit) — halkbank_mrm_report_en.xlsx","Yes"],
 ["UC-07","Assess Criticality & Apply","Criticality","1st Line, 2nd Line MRM","Model selected (opt.)","Answer the questions (M1-M5, K1-K7, B1, O1, flags) → 'Apply to model'","Model tier/class/scores updated; hard rules applied","Yes"],
 ["UC-08","Validation Record & Test Catalog","Model Validation","Recommendation/tests: 2nd Line Independent Validation · Approval: Model Risk Committee","—","New Validation → type/trigger/independence → test catalog results → RECOMMENDATION; separate APPROVAL decision","Approval 'Approved/Conditional' + report date → the model's last validation and status update automatically","Yes"],
 ["UC-09","Open Finding / Run Remediation","Findings","Open/edit: 1st Line, 2nd Lines","—","New Finding → severity (derives SLA) → action plan → evidence/re-test → advance status","Lifecycle advances; selecting 'Closed' automatically demotes to 'Pending Closure Approval'","Yes"],
 ["UC-10","Finding Closure Approval","Findings","ONLY 2nd Line (Independent Validation / MRM)","Status=Pending Closure Approval + evidence","Finding form → 'Approve Closure'","Status=Closed; approving role + date recorded","Yes"],
 ["UC-11","IFRS9 Overlay Record","PMA / Exceptions","Record: 1st/2nd line (except read-only) · Approval: ONLY Model Risk Committee","—","New Overlay → type/impact direction/amount/stage/scenario/rationale → Save → Committee Approve/Conditional/Reject","Approval status and independent review tracked; rejection → status Pending","Yes"],
 ["UC-12","Guardrail / Red-Team Test","Vendor & GenAI","1st Line, 2nd Line MRM","GenAI model exists","'+ Test Record' → type (Prompt Injection/Jailbreak/…)/result/severity","If result is 'Failed' a finding is opened automatically (High/Medium by severity)","Yes"],
 ["UC-13","Vendor Due Diligence","Vendor & GenAI","1st Line, 2nd Line MRM","Vendor model","'Edit' → transparency/SLA/exit strategy/due diligence","Vendor governance record updated","Yes"],
 ["UC-14","Model Journey Phase Actions","Model Detail → Model Journey (10 Phases)","1st Line, 2nd Line MRM","—","Phase card → Open Form (R_Sxx_n fields) / Close / Reopen / Skip","Mandatory-field completion feeds version progress; close date stamped","Yes"],
 ["UC-15","Lifecycle Transition","Lifecycle","1st Line, 2nd Lines, Committee (PERMS)","Rule-based transition exists","Transition button on the kanban card","Model status changes per rule","Yes"],
 ["UC-16","Enter Monitoring Metric / Breach","Monitoring & Metrics","1st Line, 2nd Line MRM","Model metric framework","Add measurement; on breach 'convert to finding'","Monitoring status updated; breach may generate a finding","Yes"],
 ["UC-17","Model Change Record","Model Change","1st Line, 2nd Line MRM","—","New change → materiality","Material change flags the revalidation trigger","Yes"],
 ["UC-18","Create Task from Notification","Notifications & Escalation","Relevant roles","Active notification","'Create task' (single / bulk for criticals)","Finding record opened; written to the audit trail","Yes"],
 ["UC-19","Daily Digest Email","Notifications & Escalation","All roles","—","'Preview Daily Digest Email' → mailto/copy","Digest text generated (Archer Notifications digest counterpart)","Yes"],
 ["UC-20","EU AI Act Gap → Finding","EU AI Act Compliance","1st Line, 2nd Lines","AI model selected","'Convert gaps to findings'","Missing articles opened as findings","Yes"],
 ["UC-21","BRSA Evidence Pack Output","BRSA / ICAAP","All roles","—","'⭳ CSV' or '⎙ PDF'","Audit-ready evidence set exported (BRSA_ICAAP_evidence_pack.csv)","Yes"],
 ["UC-22","Delete Model","Model Inventory","ONLY 2nd Line MRM","—","Model form → Delete","Model and linked views updated","Yes"],
 ["UC-23","JSON Backup / Restore","About","All roles","—","JSON export/import","Entire state carried (incl. guardrails) — mrm-sim-data-en.json","Yes"],
 ["UC-24","Role Switch","Top bar","All users","—","Role selector","UI permissions applied instantly (read-only, field locks, disabled buttons)","No"],
 ["UC-25","Sample Data Reset","Top bar","All roles (confirmation prompt)","—","'↺ Sample Data'","24-model seed set reloaded","Yes"],
 ["UC-26","Clear Audit Trail","Audit Trail","ONLY 2nd Line MRM (for testing)","—","'Clear audit trail'","Restricted with the note that it is immutable in production","Yes"],
 ["UC-27","Provisioning Impact Declaration","Declaration Questionnaire","1st Line, 2nd Line MRM","Declaration form open","'⚠ Model has provisioning impact' → popup: 'All potentially affected stakeholders will be notified. Do you accept?' → Confirm / Go Back","Flag recorded on confirm; PROVISION-IMPACT notification generated to Financial Reporting/IFRS9/MRM/Validation; visible on the Inventory Declaration tab","Yes"],
 ["UC-28","View Audit Record Content","Audit Trail","All roles (incl. read-only)","Record has content (chg)","Click a row in the audit trail","Drawer: action header + Field | Previous → New change table (e.g. valFrekans Annual → Biennial); LOG-##### record no","—"],
 ["UC-29","Open Model by MUID","Model Inventory","All roles","—","Type the MUID into the search box (HB-MDL-…) or call findModel(muid) programmatically","Model found/opened by its unique immutable identifier; MUID never changes on edit","—"],
 ["UC-30","Dependency Mapping (Upstream/Downstream)","New Model / Edit Model","1st Line, 2nd Line MRM","—","Section 5: two separate panels (⬆ Feeding / ⬇ Fed) — tick from the list, selections appear live in the side box → Save","Downstream selection is written BIDIRECTIONALLY to the counterpart model's upstream record; reflected instantly in the Dependency & Impact graph; a 'Dependency mapping' audit record WITH CONTENT (previous → new relation lists) is written","Yes"],
 ["UC-31","NOTA Process Mapping","New Model / Edit Model","1st Line, 2nd Line MRM","—","Section 4: 'Linked NOTA Process' dropdown (22-entry bank process catalog, thesis-style numbering: 1.1.1. Retail Credit Allocation…)","Model linked to a NOTA process; shown on the model detail General tab and as a 📌 callout on Dependency & Impact (Archer NOTA screen cross-reference)","Yes"],
 ["UC-32","Model Need Justification (mandatory)","Declaration Questionnaire","1st Line, 2nd Line MRM","—","Section 1: 'Model Need Justification — why is this model needed?' mandatory text","Save is blocked if empty; written to the model + official inventory record, shown on detail and the Inventory Declaration tab","Yes"],
]

S5 = "Very Low(1)…Very High(5)"
B = "Declaration Questionnaire"
FIELDS = [
 [B,"1 · Identity & Ownership","Model Name","text","M",""],
 [B,"1 · Identity & Ownership","Model Need Justification (why is it needed?)","text-long","M","MANDATORY — save blocked if empty"],
 [B,"1 · Identity & Ownership","Declaring Business Unit","dropdown","M","10 EVP/Group units"],
 [B,"1 · Identity & Ownership","Origin","dropdown","","In-House Development · Vendor/Third-Party · Group/Parent Model"],
 [B,"1 · Identity & Ownership","Model Status","dropdown","M","Development · In Validation · Approved/Prod · In Monitoring"],
 [B,"2 · Model Definition (PMJ)","Model Class","dropdown","M","Traditional · Econometric · ML/AI"],
 [B,"2 · Model Definition (PMJ)","Model Type","dropdown","M","ADVANCED ANALYTICS MODEL · SIMPLE MODEL"],
 [B,"2 · Model Definition (PMJ)","Model Category","dropdown","M","Credit/IRB, IFRS9 ECL, VaR, IRRBB, AML… (12)"],
 [B,"2 · Model Definition (PMJ)","Purpose / Use","dropdown","M","12 purposes"],
 [B,"2 · Model Definition (PMJ)","Methodology Family","dropdown","","11 methodologies"],
 [B,"2 · Model Definition (PMJ)","Performance Metric Framework","dropdown","M","10 frameworks — determines the monitoring metrics"],
 [B,"2 · Model Definition (PMJ)","Lifecycle Phase","dropdown","","4 phases (LC4)"],
 [B,"3 · Attributes & Criticality","AI/ML model?","dropdown","","Yes/No"],
 [B,"3 · Attributes & Criticality","GenAI / Foundation Model?","dropdown","","Yes/No"],
 [B,"3 · Attributes & Criticality","Regulatory / capital use?","dropdown","","Yes/No"],
 [B,"3 · Attributes & Criticality","Overall Criticality Level","dropdown","","Low · Medium · High · Critical (simple mode; 'Medium' assumed if empty)"],
 [B,"3 · Attributes & Criticality","Model has provisioning impact (button)","button+popup","","Popup: 'All potentially affected stakeholders will be notified. Do you accept?' — Confirm/Go Back; PROVISION-IMPACT notification on confirm"],
 [B,"4 · Materiality (S.03.A) — Advanced","M1 — Risk amount / portfolio size","dropdown","",S5],
 [B,"4 · Materiality (S.03.A) — Advanced","M2 — Customers/transactions affected","dropdown","",S5],
 [B,"4 · Materiality (S.03.A) — Advanced","M3 — Impact on decisions","dropdown","",S5],
 [B,"4 · Materiality (S.03.A) — Advanced","M4 — Solvency / regulatory capital","dropdown","",S5],
 [B,"4 · Materiality (S.03.A) — Advanced","M5 — Reputational / behavioral impact","dropdown","",S5],
 [B,"5 · Complexity (S.03.B) — Advanced","K1 — Input data nature","dropdown","",S5],
 [B,"5 · Complexity (S.03.B) — Advanced","K2 — Methodology complexity","dropdown","",S5],
 [B,"5 · Complexity (S.03.B) — Advanced","K3 — Implementation/integration","dropdown","",S5],
 [B,"5 · Complexity (S.03.B) — Advanced","K4 — Frequency of use","dropdown","",S5],
 [B,"5 · Complexity (S.03.B) — Advanced","K5 — Explainability/opacity","dropdown","",S5],
 [B,"5 · Complexity (S.03.B) — Advanced","K6 — Bias potential","dropdown","",S5],
 [B,"5 · Complexity (S.03.B) — Advanced","K7 — Autonomy/recalibration","dropdown","",S5],
 [B,"5 · Complexity — Advanced","O1 — Autonomy level","dropdown","","0-3 (min 3 if 'Direct decision' is selected)"],
 [B,"5 · Complexity — Advanced","B1 — Downstream dependency","dropdown","","0-3"],
 [B,"6 · Validation Calendar","When was the last validation?","dropdown","","This year · Last year · 2 years ago · Not yet"],
 [B,"6 · Validation Calendar","Validation Frequency","dropdown","","Auto from Tier · Annual · Biennial · Triennial · Event-Triggered · Materiality-Triggered (SR 26-2)"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Model Purpose (*)","text-long","",""],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Business Process Used In (NOTA Process etc.)","dropdown","","10 processes"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Impact on Business Decisions","dropdown","","Direct decision · Decision support · Informational (Direct→O1=3)"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Model Type","dropdown","","Statistical · Econometric · ML · GenAI · Rule-Based · Hybrid"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Modeling Approach","dropdown","","Supervised/Unsupervised/Time Series/Optimization/Rule-Based/Simulation"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Development Platform","dropdown","","Dataiku · SPSS · SAS · Excel · MATLAB · Python · R · KNIME"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Development Language","dropdown","","Python · SQL · R · SAS · MATLAB · VBA · Scala"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Algorithm Used","dropdown","","Log.Reg · Decision Tree · RF · GBM · K-Means · NN · LLM …"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Modeling Data Date Range","text","",""],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Model Development Date (**)","date","",""],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Last Model Revision Date (Refresh/Calibration)","date","",""],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Model Developer (Unit/Department or Firm)","text","",""],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Model Consultant Name (if consulting used)","text","",""],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","User Units & Departments","text","",""],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Bank Contact Person","text","","Also used as model owner"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Is a control/verification process in place?","dropdown","","Yes/No"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Is performance measured?","dropdown","","Yes/No"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","In scope of BRSA audit?","dropdown","","Yes → flagged regulatory (affects Tier)"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","In scope of internal audit?","dropdown","","Yes/No"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Is there a model document?","dropdown","","Yes/No"],
 [B,"7 · Official Halkbank Inventory Fields — Advanced","Notes (Optional) (***)","text-long","",""],
 ["Model Form (expert, 7 sections)","(summary)","S1 Identity: Name*, Owning Unit(dropdown), Owner, Origin, Supplier, Status, Developer, Validator · S2 Definition: Type, Class, Metric Framework(dropdown), Methodology, Algorithm, System, Purpose, Category(VERTICAL LIST + Selected box) · S3 Flags(annotated vertical list) · S4 Linked NOTA Process(dropdown, 22 processes) · S5 Mapping: Upstream & Downstream SEPARATE panels (tick + Selected box beside; downstream reverse-write) · S6 Dates & Frequency (incl. Materiality-Triggered) · S7 Assumptions/Limitations + 4 links","mixed","",""],
 ["Validation Form","(summary)","Title*, Model*, Type(6), Trigger(6), Validator, Independence(4), Backtest, Discriminatory Power, Effective Challenge, RECOMMENDATION(3), Rating(3), Report Date, APPROVAL decision(4)+Authority — approval fields active only in the Committee role","mixed","",""],
 ["Finding / Remediation Form","(summary)","Title*, Model, Source(5), Severity(3→SLA), Remediation Status(6 stages), Owner, 2 dates, Action Plan, Evidence/Re-test — closure approval block only for the 2nd line","mixed","",""],
 ["Overlay / Exception Form","(summary)","Model*, Type(5), Materiality, Impact Direction, Impact Amount, IFRS9 Stage, Scenario, Rationale, Calculation, Release Criterion, Approval Authority, Independent Review(4), Status + Committee approval buttons","mixed","",""],
 ["Guardrail Test Form","(summary)","Model(GenAI)*, Test Type(7), Date, Result(Passed/Failed), Severity, Detail — 'Failed' opens a finding automatically","mixed","",""],
 ["Vendor Form","(summary)","Supplier, Transparency(black/grey/transparent), SLA, Exit Strategy, Black-Box Constraint, Due Diligence(3), Last Review","mixed","",""],
 ["Phase Form (Model Journey)","(summary)","R_Sxx_n fields per phase (dropdown/text/number/date; * mandatory) — 10 phases × 3-5 fields; saving feeds progress","mixed","",""],
]

DATA_MODEL = [
 ["models","Model record (main entity)","id (MDL-####), muid (HB-MDL-XXXXXXXXXXXX — unique, IMMUTABLE; assigned at creation, preserved on edit), karsilikEtkisi (provisioning impact), notaSurec (NOTA process link), ihtiyacGerekce (mandatory justification), ad (name), tip (type), sinif (class), modelTipi, kategori[] (categories), amac (purpose), amacDetay, metricProfile, aiml, genai, deterministik, duzenleyici (regulatory), koken (origin), tedarikci (supplier), sahipBirim (owning unit), sahip (owner), gelistirici (developer), validator, metodoloji, algoritma, barindiran (hosting system), durum (status), durumTalep (requested status), wf (mrm/komite/aktif/red), gelistirmeTarihi, prodTarihi, sonValidasyon, valFrekans, izlemeDurumu, upstream[], links{doc,monitor,repo,val}, kaynak (source), crit{M1-M5,K1-K7,B1,O1,duzenleyici,genai}, mat, kar, icsel, tier, derece, envanter{23 official fields,_auto}, vendor{}, phases[10], aimlEk{}, lifecyclePhase","Model Inventory application"],
 ["validations","Independent validation record","id (VAL-####), baslik (title), modelId, tur (type), tetik (trigger), validator, bagimsizlik (independence), backtest, ayrimGucu, eskSorgu (effective challenge), oneri (recommendation), rating, onayKarar (approval decision), onayMakam, raporTarihi, durum, tests{11 tests}","Validation application"],
 ["findings","Finding / remediation","id (FND-####), baslik, modelId, kaynak (source), onem (severity), durum (6 stages), sahip (owner), olusturma, hedefTarih, aksiyon, kanit (evidence), kapanisOnay, kapanisTarih","Findings/Issues"],
 ["metrics","Metric measurements","id (MET-####), modelId, tarih, tur (18 metrics incl. Hallucination/Toxicity), deger (value), esik (threshold) — last 6 months generated dynamically","Metric Results sub-form"],
 ["pmas","Overlay / exception","id (PMA-####), modelId, tur, materyalite, yon, etkiTutar, tfrs9Asama, senaryo, gerekce, hesaplama, kaldirma, onayMakam, bagimsizGozdenDurum, durum, onayDurum","PMA sub-form + workflow"],
 ["changes","Model changes","id (CHG-####), modelId, versiyon, tur, aciklama, materyalite, revalidasyon, onay, tarih","Change sub-form"],
 ["guardrails","GenAI guardrail/red-team","id (GRD-####), modelId, tarih, tur (7 tests), sonuc (result), siddet (severity), detay","Sub-form"],
 ["audit","Audit trail","aid (LOG-#####), ts, role, action, entity, detail, chg[] = field-level change content {alan, eski, yeni} (max 500 records)","History Log + field history"],
 ["tmrHistory","TMR index trend","d (date), i (index 0-100) — daily, max 90","Calculated field history"],
 ["appetite","Risk appetite thresholds","overdue, highFindings, breach, pending, amber(40), red(60)","Parameter record"],
 ["selfAssessment","Self-assessment","attestDate, attestBy","Attestation"],
]

ROLES_HDR = ["Action","1st Line – Owner/Developer","2nd Line – Independent Validation","2nd Line – MRM Program","Model Risk Committee","3rd Line – Internal Audit"]
ROLES = [
 ["Create/Edit model (declaration, form, CSV)","✓","·","✓","·","·"],
 ["Delete model","·","·","✓","·","·"],
 ["Set criticality/tier","✓","·","✓","·","·"],
 ["Final tier confirmation","·","✓","✓","·","·"],
 ["Validation recommendation/testing","·","✓","·","✓","·"],
 ["Approval decision (validation)","·","·","·","✓","·"],
 ["Model approval workflow — MRM step","·","·","✓","·","·"],
 ["Model approval workflow — Committee step","·","·","·","✓","·"],
 ["Overlay (IFRS9/PMA) approval","·","·","✓","✓","·"],
 ["Enter monitoring metric","✓","·","✓","·","·"],
 ["Model change","✓","·","✓","·","·"],
 ["Lifecycle transition","✓","✓","✓","✓","·"],
 ["Finding / remediation","✓","✓","✓","·","·"],
 ["Finding CLOSURE approval","·","✓","✓","·","·"],
 ["Guardrail test / Vendor record","✓","·","✓","·","·"],
 ["Clear audit trail (testing)","·","·","✓","·","·"],
 ["Read-only view","·","·","·","·","✓"],
]

CALCS = [
 ["Materiality score","M1×0.30 + M2×0.15 + M3×0.25 + M4×0.20 + M5×0.10 (1-5 scale)","Weights Σ=1.00"],
 ["Complexity score","K1×0.18 + K2×0.20 + K3×0.12 + K4×0.10 + K5×0.15 + K6×0.10 + K7×0.15","Weights Σ=1.00"],
 ["Inherent Risk","Materiality × Complexity (1-25)","—"],
 ["Tier assignment","≥15 → Tier 1 · ≥8 → Tier 2 · ≥3 → Tier 3 · <3 → Negligible","Risk Class: Tier1→Class1 … Negligible→Class4"],
 ["Hard rule 1","Regulatory/capital use → minimum Tier 2","'Negligible' not allowed"],
 ["Hard rule 2","Fully autonomous decision (O1=3) → minimum Tier 2","'Direct decision' in the declaration → O1=3"],
 ["Hard rule 3","GenAI/foundation model → minimum Tier 2","AI/ML extra assessment mandatory"],
 ["Hard rule 4","Downstream dependency B1=3 → tier raised one level","—"],
 ["Conservative default","If no criticality is entered in the declaration, the 'Medium' preset (M/K=3) applies","An uninformative declaration can never fall into Negligible"],
 ["Validation frequency","Tier 1→Annual · Tier 2→Biennial · Tier 3→Triennial · Negligible→Event-Triggered; manual override incl. Materiality-Triggered (SR 26-2)","Next val. = last val. + frequency (DATEADD); Event-/Materiality-Triggered have no calendar date"],
 ["Overdue status","Next date passed→Overdue · <45 days→Upcoming · otherwise On Track","—"],
 ["Finding SLA","High 30 days · Medium 60 · Low 90 (added to creation date)","<14 days → Upcoming"],
 ["TMR Index (0-100)","Structural risk (tier mix, weight 40) + Overdue validations (20) + Open high findings (15) + Monitoring breaches (15) + Conditional approval load (10)","Tier weights: T1=1.0, T2=0.66, T3=0.33, Negligible=0.1"],
 ["TMR RAG","≥60 → Appetite BREACHED (red) · ≥40 → Amber · <40 → Within appetite","Thresholds from the appetite record; daily trend stored"],
 ["Appetite limits","Overdue val=0 · Open high findings≤3 · Breaches≤2 · Pending approvals≤5","—"],
 ["Metric thresholds (tier-based)","e.g. PSI: T1 0.10 · T2 0.20 · T3 0.25 · Negligible 0.30; AUC: T1 0.75 · T2 0.70 · T3 0.65","18 metrics; direction (↑good/↓good/band) in the metric definition"],
 ["Threshold breach","dir=low: value>threshold · dir=high: value<threshold · band: outside the band","Breach → monitoring status + convertible to finding"],
 ["ICAAP mapping","Credit/IRB→Credit Risk · IFRS9→Provisioning · VaR→Market · CVA→Counterparty · IRRBB→Pillar 2 · ICAAP→Capital · AMA→Operational","Regulatory models only"],
 ["MUID generation","HB-MDL- + 12 hex (crypto.getRandomValues); assigned at creation; saveModel forcibly preserves the previous value on edit","Immutability guaranteed at the application layer; key field (read-only) in Archer"],
 ["Metric generation","Last 6 months (dynamic) series per model framework; models flagged _degrade breach the threshold in the last 2 months","Automatic for declared/CSV models"],
]

NOTIF_RULES = [
 ["Overdue validation","Critical","Model Owner / MRM","Next validation date passed"],
 ["Upcoming validation (45 days)","Warning","Model Owner","—"],
 ["Monitoring threshold breach","Critical","Model Owner / Validation","Metric threshold breached — remediation"],
 ["Conditional approval trigger","Warning","Independent Validation","Conditions must be resolved in time"],
 ["Finding SLA overdue","Critical","Finding Owner","Target date passed"],
 ["Awaiting approval (validation/model/overlay)","Info","Model Risk Committee / MRM","—"],
]
MAIL_RULES = [
 ["Upcoming validation (45 days)","Model Owner + Validator","VAL-REMINDER","Weekly digest"],
 ["Overdue validation","Owner + MRM Program + Committee","VAL-OVERDUE","Daily"],
 ["Monitoring breach (errors raised)","Model Owner + Independent Validation","METRIC-BREACH","Immediate"],
 ["Finding SLA (findings written)","Finding Owner + MRM Program","FND-SLA","Daily"],
 ["Model / overlay awaiting approval","Approval authority (MRM / Committee)","APPROVAL-PENDING","Daily"],
 ["Guardrail / red-team failure","AI Model Owner + MRM Program","GRD-FAIL","Immediate"],
 ["Provisioning impact declaration","Financial Reporting + IFRS9 Team + MRM + Validation","PROVISION-IMPACT","Immediate"],
 ["Weekly MRM management digest","MRM Program + Senior Management","WEEKLY-DIGEST","Weekly (Mon 08:00)"],
]

OUTPUTS = [
 ["XLSX Report (10 sheets)","Top bar button","Summary(Board) · Model Inventory · Validations · Validation Plan · Findings · Overlay-PMA · Guardrails · Latest Metrics · BRSA Evidence · Audit Trail — file: halkbank_mrm_report_en.xlsx","Pure-JS xlsx writer (no external library); Archer Reporting/mail-merge counterpart"],
 ["Inventory CSV export","Model Inventory","Model ID, MUID, Model Name, Business Unit, Class, Model Type, Category, Status, Metric Framework, Regulatory, AI/ML, Overall Criticality, Last Validation, Tier, Inherent Risk, Source — file: halkbank_model_inventory_en.csv","Also serves as the import template"],
 ["CSV bulk import","Model Inventory","Flexible header matching (EN: model name / business unit / class / model type / category / status / metric / regulat / ai / critic / last val); mandatory: Model Name; Tier/metrics/calendar automatic; records enter the approval workflow","Archer Data Import / Data Feed Manager"],
 ["BRSA evidence CSV/PDF","BRSA / ICAAP","Model, Tier, ICAAP link, validation currency, open findings, overlays — file: BRSA_ICAAP_evidence_pack.csv","Reporting"],
 ["JSON backup/restore","About","Entire state (models, validations, findings, metrics, pmas, changes, guardrails, audit, tmrHistory) — file: mrm-sim-data-en.json","Portability/testing"],
 ["Daily digest email","Notifications","Digest text + mailto: + copy to clipboard (to mrm.program@halkbank.com.tr)","Notifications digest"],
 ["Data Feed / API (simulation)","Data Feed","Feed definitions and sample payload view","Data Feed Manager / REST API"],
 ["Board report (print)","Risk Dashboard","PDF via window.print","Report"],
]

FED = "US Fed / OCC"; FEDDOC = "SR 11-7 (superseded by SR 26-2, Apr 2026 — principle carried forward)"
CITES = [
 ["Establishing MRM as a separate risk discipline (whole console)","Bank of England (PRA)","SS1/23, §1.4","The PRA's desired outcome is that firms take a strategic approach to MRM as a risk discipline in its own right.","A dedicated console that manages model risk as a discipline in its own right, like credit or market risk."],
 ["Model definition & scope (all models/algorithms in the inventory)",FED,FEDDOC+", 'Overview of Model Risk Management'","...the term model refers to a quantitative method, system, or approach that applies statistical, economic, financial, or mathematical theories, techniques, and assumptions to process input data into quantitative estimates.","This definition underlies the inventory scope (statistical/econometric/AI-ML/rule-based) and the EUC flag. SR 26-2 narrows the definition toward complex quantitative methods — the deterministic/EUC flag supports that triage."],
 ["Firm-wide Model Inventory screen",FED,FEDDOC+", 'Model Inventory'","Banks should maintain a comprehensive set of information for models implemented for use, under development for implementation, or recently retired.","The inventory covers every status (Development→Retired); the unit×class matrix shows the whole bank."],
 ["Inventory field set + MUID (immutable id) + 'evergreen' currency","OSFI (Canada)","Guideline E-23 (2027), §C.1","An institution's model inventory should be... accurate, evergreen, and subject to robust controls...","Unique immutable MUID, audit trail and approval workflow are the systemic counterpart of 'accurate, evergreen and controlled'."],
 ["Dependencies in the inventory + Dependency & Impact page","Bank of England (PRA)","SS1/23, Principle 1.2","A comprehensive model inventory should be maintained to enable firms to: identify the sources of model risk; provide the management information needed for reporting model risk; and help to identify model inter-dependencies.","Upstream/downstream relation panels and the network graph implement 'model inter-dependencies' directly."],
 ["Criticality Assessment → Tier 1-3/Class (risk-based tiering)","Bank of England (PRA)","SS1/23, Principle 1.3","Risk-based model tiering should be used to prioritise validation activities and other risk controls through the model lifecycle, and to identify and classify those models that pose most risk to a firm's business activities, and/or firm safety and soundness.","Tier assignment from the Materiality×Complexity score, and tier-driven validation frequency/thresholds, derive from this principle."],
 ["Independent Validation + RECOMMENDATION ≠ APPROVAL (effective challenge)",FED,FEDDOC+", 'Overview'","A guiding principle for managing model risk is 'effective challenge' of models, that is, critical analysis by objective, informed parties who can identify model limitations and assumptions and produce appropriate changes.","The validation test catalog + effective-challenge notes field rest on this principle."],
 ["Validation independence (role separation, field locks)",FED,FEDDOC+", 'Model Validation'","Validation involves a degree of independence from model development and use. Generally, validation should be done by people who are not responsible for development or use and do not have a stake in whether a model is determined to be valid.","Recommendation/rating fields only in the independent validation role; approval in a separate authority (segregation of duties)."],
 ["Validation Plan — annual/risk-based calendar + overdue alerts",FED,FEDDOC+", 'Model Validation'","Banks should conduct a periodic review—at least annually but more frequently if warranted—of each model to determine whether it is working as intended and if the existing validation activities are sufficient.","12-month calendar, tier-based frequency (T1 annual) and 'Overdue' alerts operationalise this sentence. SR 26-2 moves toward materiality-based cycles — hence the new 'Materiality-Triggered' frequency option."],
 ["Monitoring & Metrics (PSI/AUC thresholds, drift → action)",FED,FEDDOC+", 'Ongoing Monitoring'","Ongoing monitoring is essential to evaluate whether changes in products, exposures, activities, clients, or market conditions necessitate adjustment, redevelopment, or replacement of the model and to verify that any extension of the model beyond its original scope is valid.","Metric time series, tier-based thresholds and breach→finding automation come from here."],
 ["Backtesting requirement","BRSA (Turkey)","ICAAP (İSEDES) Regulation, art. 42/6","Risk ölçüm yöntemi veya modelinin doğruluğu ve güvenilirliği, gerçekleşen sonuçlar kullanılarak geriye dönük testler yoluyla tespit edilir. [EN gist: the accuracy and reliability of a risk measurement method or model shall be established through backtesting against realised outcomes.]","The backtesting item in the validation test catalog and the monitoring series implement this provision."],
 ["Validation definition (BRSA alignment)","BRSA (Turkey)","ICAAP (İSEDES) Regulation, art. 3/1(ll)","Validasyon: Metodoloji kapsamında kullanılan modellerin gerçekleşmeleri hangi oranda temsil ettiğini kesinlik, doğruluk ve tutarlılık ölçüleri kullanılarak belirlenmesi ve metodolojinin diğer unsurlarının sağlamlığının değerlendirilmesini [ifade eder]. [EN gist: validation means determining, using measures of precision, accuracy and consistency, the extent to which models represent realised outcomes, and assessing the soundness of the other elements of the methodology.]","The validation test set (precision/accuracy/consistency) is aligned with this definition; the BRSA/ICAAP Evidence page reports the linkage."],
 ["Total Model Risk Index (aggregate risk)",FED,FEDDOC+", 'Overview'","Banks should consider risk from individual models and in the aggregate. Aggregate model risk is affected by interaction and dependencies among models; reliance on common assumptions, data, or methodologies; and any other factors that could adversely affect several models and their outputs at the same time.","The 0-100 TMR index + dependency network is the dashboard for the 'aggregate model risk' expectation."],
 ["Risk appetite thresholds (board indicator)","Bank of England (PRA)","SS1/23, Principle 2","Firms should have strong governance oversight with a board that promotes an MRM culture from the top through setting clear model risk appetite.","Amber/red appetite thresholds and the one-page board summary rest on this principle."],
 ["Board/senior management governance",FED,FEDDOC+", 'Governance'","Model risk governance is provided at the highest level by the board of directors and senior management when they establish a bank-wide approach to model risk management.","The Risk Dashboard & Board screen + self-assessment/attestation present this framework."],
 ["IFRS9 ECL Overlay (PMA) governance + independent review","Bank of England (PRA)","SS1/23, Principle 5","Firms should have established policies and procedures for the use of model risk mitigants when models are under-performing, and should have procedures for the independent review of post-model adjustments.","Overlay records (impact/stage/scenario), Committee approval and the independent review field implement P5 directly."],
 ["Accounting basis of overlays (forward-looking information)","IASB","IFRS 9, para. 5.5.17(c)","...reasonable and supportable information that is available without undue cost or effort at the reporting date about past events, current conditions and forecasts of future economic conditions.","The need for an overlay on ECL under macro uncertainty arises from this paragraph; the record carries a scenario link field."],
 ["Use exception / PMA escalation","Bank of England (PRA)","SS1/23, Principle 5.3","Exceptions for model use should be temporary, should be subject to post-model adjustments (PMAs), should be reported to and supported by stakeholders and senior management.","Exception records are modelled with temporariness + release criterion + approval authority fields."],
 ["Finding remediation + restricted use",FED,FEDDOC+", 'Model Validation'","If significant deficiencies are noted as a result of the validation process, use of the model should not be allowed or should be permitted only under very tight constraints until those issues are resolved.","The finding lifecycle (evidence + 2nd-line closure approval) and the 'Restricted/Suspended' status apply this provision."],
 ["Model Change → revalidation on material change",FED,FEDDOC+", 'Model Validation'","Material changes to models should also be subject to validation.","The materiality field on the change record flags the revalidation trigger."],
 ["Vendor & third-party model governance",FED,FEDDOC+", 'Third-Party Products' (SR 26-2 adds a dedicated vendor/third-party section)","Vendor products should nevertheless be incorporated into a bank's broader model risk management framework following the same principles as applied to in-house models, although the process may be somewhat modified.","The Vendor screen (due diligence, SLA, exit strategy, black-box constraint) implements this sentence."],
 ["Model Journey — 10-phase lifecycle","OSFI (Canada)","Guideline E-23 (2027), §A definitions","Model lifecycle components are model design (including model rationale, data, and development), model review, model deployment, model monitoring, and model decommission.","The 10-phase stepper + phase form engine manages the lifecycle end to end; E-23 Outcome: 'Model risk is managed using a risk-based approach.'"],
 ["EU AI Act compliance tracker (high-risk AI) — obligations in force since 2 Aug 2026","European Union","AI Act (2024/1689), Article 9(1)-(2)","A risk management system shall be established, implemented, documented and maintained in relation to high-risk AI systems. / The risk management system shall be understood as a continuous iterative process planned and run throughout the entire lifecycle of a high-risk AI system, requiring regular systematic review and updating.","The article-based tracker and gap→finding automation bring this obligation to life."],
 ["GenAI guardrail / red-team log (Generative & Agentic AI)","European Union","AI Act (2024/1689), Article 15(1) and 15(5)","High-risk AI systems shall be designed and developed in such a way that they achieve an appropriate level of accuracy, robustness, and cybersecurity... / High-risk AI systems shall be resilient against attempts by unauthorised third parties to alter their use, outputs or performance by exploiting system vulnerabilities.","Prompt injection/jailbreak/red-team test records and automatic findings on failure are the test evidence for the 'robustness/resilience' provisions."],
 ["Audit trail + action content (field-level before→after)",FED,FEDDOC+", 'Documentation'","Without adequate documentation, model risk assessment and management will be ineffective.","Immutable audit trail + clickable field-level change content (Archer History Log) derive from this principle."],
]

# ------------------------------------------------------------------ sheets
# 1) Cover & Guide
ws = wb.active; ws.title = "Cover & Guide"
ws.column_dimensions["A"].width = 30; ws.column_dimensions["B"].width = 110
ws.cell(1,1,"HALKBANK — MRM CONSOLE (ENGLISH EDITION)").font = font(20, True, NAVY)
ws.cell(2,1,"Model Risk Management Simulation — Software Development Specification & Handover (for /mrm-en)").font = font(12, True, RED)
ws.cell(3,1,"All menus, screens, use cases, forms, roles, calculations and Archer mappings — English twin of MRM_Konsolu_Yazilim_Tanitim.xlsx").font = font(10, False, GREY)
for r in (1,2,3): ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
meta = [
 ("Document","MRM Console — Software Development Specification (EN)"),
 ("Version",f"v1.4-EN — English edition of v1.3 + regulation refresh (SR 26-2, EU AI Act in force, Materiality-Triggered cycle)"),
 ("Date",DATE),
 ("Live application (EN)",APP_URL),
 ("Turkish edition",TR_URL+"  (same code base; separate localStorage key)"),
 ("Source code","repo: drumutbsby/rrr → mrm-archer/simulation-en/index.html (single-file HTML/CSS/JS)"),
 ("Rollback","Turkish edition snapshots: /mrm/v1/ · /mrm/v2/ (permanent URL copies). The EN edition is generated from the TR source by a verified dictionary translation (1,570 entries); logic is identical."),
 ("Target platform","RSA Archer (IRM) — every feature is mapped to the relevant Archer mechanism"),
 ("Scope note","The application is a browser-based simulation (localStorage key mrm_sim_en_v1); this document is the functional specification of what is to be built in Archer."),
 ("EN-specific differences","UI, option values, seed data, audit labels, CSV/XLSX outputs and e-mail templates are English; Turkish terms are mapped IFRS 9 (TFRS 9), ECL (BKZ), ICAAP (İSEDES), BRSA (BDDK). The Halkbank logo is replaced by a neutral 'MRM' mark. Internal JSON property names (ad, durum, sahipBirim…) are UNCHANGED for code compatibility — see Data Model."),
 ("Regulation refresh (Oct 2026)","SR 11-7 was superseded by SR 26-2 (Fed/OCC/FDIC, 17 Apr 2026); all screen references updated. EU AI Act Annex III obligations in force since 2 Aug 2026. 'Materiality-Triggered' validation frequency added (SR 26-2 materiality-based cycles)."),
]
r = 5
for k, v in meta:
    ws.cell(r,1,k).font = font(10, True, NAVY); c = ws.cell(r,2,v); c.font = font(10); c.alignment = Alignment(wrap_text=True, vertical="top"); r += 1
r += 1
ws.cell(r,1,"SHEET GUIDE").font = font(12, True, NAVY); r += 1
for i,h in enumerate(["Sheet","Content"],1):
    c=ws.cell(r,i,h); c.font=font(10,True,"FFFFFF"); c.fill=PatternFill("solid",fgColor=NAVY)
r += 1
guide = [
 ("Menu Inventory",f"Purpose, components and Archer counterpart of {len(MENUS)-1} screens + top bar"),
 ("Use Cases",f"All {len(UCS)} user actions: actor, precondition, flow, outcome, audit trail"),
 ("Forms & Fields",f"Declaration questionnaire (7 sections) and all form fields: type, mandatory flag, options ({len(FIELDS)} rows)"),
 ("Data Model","state entities and field dictionary (internal keys unchanged)"),
 ("Roles & Permissions","Role × action matrix + special permission rules (segregation of duties)"),
 ("Calculations","Criticality/Tier score, TMR index, SLA, frequency, metric thresholds, ICAAP mapping"),
 ("Notifications & Email","Rule engine + Archer Notifications e-mail request (8 rules)"),
 ("Outputs & Integration","XLSX (10 sheets), CSV in/out, JSON, BRSA pack, mailto"),
 ("Basis & Citations","Regulatory basis of EVERY feature: authority + document + section + VERBATIM SENTENCE from the original text (for management presentation)"),
]
for n,(k,v) in enumerate(guide):
    a=ws.cell(r,1,k); a.font=font(10,True); b=ws.cell(r,2,v); b.font=font(10)
    if n%2==1:
        for c in (a,b): c.fill=PatternFill("solid",fgColor=ZEBRA)
    r+=1
r += 1
ws.cell(r,1,"Summary counts (computed by the build script — static document):").font = font(10, True, NAVY); r+=1
for k,v in [("Number of screens",len(MENUS)),("Defined use cases",len(UCS)),("Form field rows",len(FIELDS)),("Citation rows",len(CITES))]:
    ws.cell(r,1,k).font=font(10); ws.cell(r,2,v).font=font(10); r+=1

# 2) Basis & Citations
ws = wb.create_sheet("Basis & Citations")
end = add_table(ws, "Basis & Citations — Feature → Regulatory Source → Original Sentence",
 "Quotes are taken VERBATIM from the source texts (verified against official PDFs/texts). Abbreviations: SR 11-7 = Fed SR 11-7 / OCC 2011-12 (04.04.2011), superseded by SR 26-2 (17.04.2026) — SR 26-2 keeps the same three-component architecture, so the quoted principles carry forward; verbatim SR 26-2 wording is to be added once verified against the official letter · SS1/23 = Bank of England PRA SS1/23 (May 2023) · E-23 = OSFI Guideline E-23 (2027) · AI Act = Regulation (EU) 2024/1689 · İSEDES Reg. = BRSA, Official Gazette 11.07.2014-29057 (quoted in Turkish with an English gist in brackets) · IFRS 9 = IASB",
 ["Feature in the application","Source authority","Document · Section","SENTENCE IN THE ORIGINAL TEXT (verbatim quote)","Why / Our implementation"],
 CITES, [30,18,30,78,44])
ws.cell(end+1,1,"Source access: SR 11-7 federalreserve.gov/boarddocs/srletters/2011/sr1107a1.pdf · SR 26-2 federalreserve.gov/supervisionreg/srletters/sr2602.htm · SS1/23 bankofengland.co.uk (PS6/23 annex) · OSFI E-23 osfi-bsif.gc.ca · AI Act eur-lex.europa.eu (2024/1689) · İSEDES Reg. Official Gazette 11.07.2014-29057 · IFRS 9 ifrs.org. Quotes are transcribed verbatim from these official texts; square brackets [ ] are editorial completions, an ellipsis (…) marks an omitted passage.").font = font(9, False, GREY)
ws.merge_cells(start_row=end+1, start_column=1, end_row=end+1, end_column=5)

# 3) Menu Inventory
ws = wb.create_sheet("Menu Inventory")
add_table(ws, f"Menu Inventory — {len(MENUS)-1} Screens + Top Bar", "Left navigation + top bar; each row is one screen/menu item",
 ["Screen ID","Group","Menu Name","Purpose / Scope","Main Components","Archer Counterpart"], MENUS, [12,15,26,60,38,26])

# 4) Use Cases
ws = wb.create_sheet("Use Cases")
add_table(ws, "Use Cases — Action Catalog", "Actor = roles authorised to perform the action; every action is written to the audit trail",
 ["ID","Action","Screen","Actor (Authorised Roles)","Precondition","Flow (summary)","Outcome / System Behaviour","Audit Trail"], UCS, [8,28,22,30,20,44,50,10])

# 5) Forms & Fields
ws = wb.create_sheet("Forms & Fields")
add_table(ws, "Forms & Field Dictionary", "M = mandatory · Control type: dropdown/text/date/number/multi-check · The declaration questionnaire fully covers the official Halkbank inventory template",
 ["Form","Section","Field / Content","Control Type","M","Options / Note"], FIELDS, [24,36,54,12,5,50])

# 6) Data Model
ws = wb.create_sheet("Data Model")
add_table(ws, "Data Model — state Entities", "localStorage key: mrm_sim_en_v1 · Internal property names are kept in their original (Turkish) form so that TR and EN editions share one code base; English meaning given in brackets · In Archer every entity becomes an application/sub-form",
 ["Entity","Description","Fields","Archer Counterpart"], DATA_MODEL, [14,26,110,26])

# 7) Roles & Permissions
ws = wb.create_sheet("Roles & Permissions")
end = add_table(ws, "Roles & Permission Matrix", "✓ = authorised · Enforced both in the UI (button/field locks) and at action level (guard functions)",
 ROLES_HDR, ROLES, [40,22,24,20,20,20])
ws.cell(end+2,1,"Special rules: default role is 1st Line. RECOMMENDATION ≠ APPROVAL (validation independence). For the 3rd Line all primary buttons + declaration entry are locked via CSS; action functions (guardWrite/roleGuard/roGuard) also block programmatically. Approval steps are enforced with segregation of duties.").font=font(9.5)
ws.merge_cells(start_row=end+2, start_column=1, end_row=end+2, end_column=6)
ws.cell(end+2,1).alignment=Alignment(wrap_text=True, vertical="top")

# 8) Calculations
ws = wb.create_sheet("Calculations")
add_table(ws, "Calculation Rules", "Implemented in Archer as calculated fields / questionnaire scoring",
 ["Calculation","Rule","Note"], CALCS, [26,84,44])

# 9) Notifications & Email
ws = wb.create_sheet("Notifications & Email")
ws.cell(1,1,"Notification Engine + E-mail Request (Archer Notifications)").font=font(14,True,NAVY)
ws.cell(2,1,"Upper block: in-app rule engine · Lower block: e-mail configuration requested from Software Development").font=font(9,False,GREY)
ws.cell(3,1,"A) In-app notification engine").font=font(12,True,NAVY)
r = 4
for i,h in enumerate(["In-app Rule","Severity","Target Role","Detail"],1):
    c=ws.cell(r,i,h); c.font=font(10,True,"FFFFFF"); c.fill=PatternFill("solid",fgColor=NAVY); c.border=border
r+=1
for n,row in enumerate(NOTIF_RULES):
    for i,v in enumerate(row,1):
        c=ws.cell(r,i,v); c.font=font(9.5); c.border=border; c.alignment=Alignment(wrap_text=True,vertical="top")
        if n%2==1: c.fill=PatternFill("solid",fgColor=ZEBRA)
    r+=1
r+=2
ws.cell(r,1,"B) SOFTWARE REQUEST — Archer Notifications e-mail rules").font=font(12,True,NAVY); r+=1
hdr=r
for i,h in enumerate(["Trigger (upcoming duties / errors / findings)","Recipient (role)","Template Code","Frequency"],1):
    c=ws.cell(r,i,h); c.font=font(10,True,"FFFFFF"); c.fill=PatternFill("solid",fgColor=NAVY); c.border=border
r+=1
for n,row in enumerate(MAIL_RULES):
    for i,v in enumerate(row,1):
        c=ws.cell(r,i,v); c.font=font(9.5); c.border=border; c.alignment=Alignment(wrap_text=True,vertical="top")
        if n%2==1: c.fill=PatternFill("solid",fgColor=ZEBRA)
    r+=1
ws.auto_filter.ref=f"A{hdr}:D{hdr+len(MAIL_RULES)}"; ws.freeze_panes=ws.cell(hdr+1,1)
r+=1
ws.cell(r,1,"Request: these rules are to be implemented as e-mails via Archer Notifications + Advanced Workflow notification templates and scheduled report/digest. The application contains an outbox simulation and a daily digest preview (mailto).").font=font(9.5,False,RED)
ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=4); ws.cell(r,1).alignment=Alignment(wrap_text=True,vertical="top")
for col,w in zip("ABCD",[46,40,20,22]): ws.column_dimensions[col].width=w

# 10) Outputs & Integration
ws = wb.create_sheet("Outputs & Integration")
add_table(ws, "Outputs & Integration Points", "Exports/imports and their Archer integration counterparts",
 ["Output / Integration","Where","Content / Columns","Note / Archer"], OUTPUTS, [26,20,76,40])

wb.save(OUT)
print("saved", OUT, "| sheets:", wb.sheetnames)
print("counts: menus", len(MENUS), "ucs", len(UCS), "fields", len(FIELDS), "cites", len(CITES))
