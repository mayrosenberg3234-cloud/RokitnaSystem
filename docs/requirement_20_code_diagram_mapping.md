# דרישה 20 — מיפוי מלא בין הקוד לתרשימים

מסמך זה נועד למיפוי החי בכיתה. הקוד יושר כך שיתאים ל-**Sequence Diagram** ול-
**Class Diagram** (תרשים 3) של חלק ב'. לכן תרשימי חלק ב' של דרישה 20 נשארים
בתוקף, והקוד מצביע עליהם הודעה אחר הודעה.

## הדרישה העסקית
מנהל המשרד מבקש דוח בקרה ניהולי. המערכת אוספת מידע מהפרויקטים **הפעילים** —
אבני דרך, דרישות תשלום, תשלומים והתראות — מאחדת אותם לדוח ניהולי אחד, שומרת את
ההפקה בבסיס הנתונים ומציגה את הדוח (כולל ייצוא ל-CSV).

## מיפוי Class Diagram → קוד

| אלמנט בתרשים (תרשים 3) | מיקום בקוד | הערה |
|---|---|---|
| `ReportDashboardForm` | `views/report_dashboard.py` | מחלקת User Class אמיתית |
| `ReportController` | `controllers/report_controller.py` | תיאום התהליך |
| `Report` (type, createDate, criteria, status) | `models/report.py` | + `generate_management_report()` |
| `Project` | `models/project.py` | `find_active_projects()` ב-Repository |
| `Milestone` | `models/milestone.py` | |
| `PaymentRequest` / `Payment` | `models/payment_request.py`, `models/payment.py` | |
| `Alert` | `models/alert.py` | |
| `DBRepository` | `repositories/db_repository.py` | שכבת הגישה היחידה ל-SQL |

## מיפוי Sequence Diagram → קוד (message אחר message)

| # | Message בתרשים | Method בקוד | קובץ |
|---:|---|---|---|
| 1 | `openReportsDashboard()` | `ReportDashboardForm.render()` | `views/report_dashboard.py` |
| 2 | `displayReportOptions()` | `ReportDashboardForm.display_report_options()` | `views/report_dashboard.py` |
| 3 | `selectReportCriteria()` | `display_report_options()` (selectbox) | `views/report_dashboard.py` |
| 4 | `validateReportCriteria()` | `ReportController._validate_report_criteria()` | `controllers/report_controller.py` |
| — | `alt [missing report criteria] → validationFailed` | `ReportCriteriaError` → `ActionResult.fail` | `controllers/report_controller.py` |
| — | `displayValidationError()` | `ReportDashboardForm.display_validation_error()` | `views/report_dashboard.py` |
| 5 | `getActiveProjects()` | `ReportController._get_active_projects()` | `controllers/report_controller.py` |
| 6 | `findActiveProjects()` | `DBRepository.find_active_projects()` | `repositories/db_repository.py` |
| 7 | `getMilestonesStatus(projectsList)` | `ReportController._get_milestones_status()` | `controllers/report_controller.py` |
| 8 | `findMilestones(projectsList)` | `DBRepository.find_milestones_by_projects()` | `repositories/db_repository.py` |
| 9 | `getPaymentRequests(projectsList)` | `ReportController._get_payment_requests()` | `controllers/report_controller.py` |
| 10 | `findPaymentRequests(projectsList)` | `DBRepository.find_payment_requests_by_projects()` | `repositories/db_repository.py` |
| 11 | `getProjectAlerts(projectsList)` | `ReportController._get_project_alerts()` | `controllers/report_controller.py` |
| 12 | `findAlerts(projectsList)` | `DBRepository.find_alerts_by_projects()` | `repositories/db_repository.py` |
| 13 | `<<create>> Report` | `Report(report_type=MANAGEMENT, criteria=...)` | `controllers/report_controller.py` |
| 14 | `generateManagementReport()` | `Report.generate_management_report(...)` | `models/report.py` |
| 15 | `saveReport(report)` | `ReportController._save_report()` → `DBRepository.save_report()` | `controllers/`, `repositories/` |
| 16 | `reportReady` (return) | `ActionResult.ok(data=report)` | `controllers/report_controller.py` |
| 17 | `displayManagementReport()` | `ReportDashboardForm.display_management_report()` | `views/report_dashboard.py` |

הסדר הלוגי בקוד (בתוך `generate_management_report`) זהה לסדר ההודעות בתרשים:
הרשאה → ולידציה → איסוף פרויקטים פעילים → אבני דרך → דרישות תשלום → התראות →
יצירת `Report` → `generate_management_report()` → `save_report()` → החזרת התוצאה
להצגה.

## מיפוי State Diagram (דרישה 20) → קוד

| מצב בתרשים | ייצוג בקוד |
|---|---|
| `ReportRequested` / `ReportRejected` | `_validate_report_criteria()` (תקין / נכשל) |
| `CollectingProjectData` | `_get_active_projects()` |
| `CheckingMilestones` | `_get_milestones_status()` |
| `CheckingPayments` | `_get_payment_requests()` |
| `ReportGenerated` | `Report.generate_management_report()` → `ReportStatus.GENERATED` |
| `ReportSaved` | `DBRepository.save_report()` → `ReportStatus.SAVED` |
| `ReportDisplayed` | `display_management_report()` |

הערה: ב-`ReportStatus` נשמרים שלושת המצבים המהותיים (`Requested`, `Generated`,
`Saved`). תת-המצבים `CheckingMilestones` / `CheckingPayments` ממומשים כשלבי איסוף
רציפים בתוך `generate_management_report`.

## תרחיש הדגמה מומלץ
1. התחברי כ-`manager` / `1234`, מסך **הפקת דוחות**.
2. נסי ללחוץ "הפק דוח" ללא בחירת קריטריון — תוצג שגיאת ולידציה
   (`validateReportCriteria`).
3. בחרי "כל הפרויקטים הפעילים" והפיקי את הדוח.
4. הציגי שהדוח כולל **רק** את שני הפרויקטים הפעילים (הפרויקט שהושלם אינו מופיע).
5. הציגי את חותמת הזמן בהיסטוריית הדוחות ובטבלת `Reports` ב-SQL.
6. הורידי את קובץ ה-CSV כתוצר נוסף עם חותמת זמן.
