# שינויים שבוצעו בקוד — דרישה 20

מטרה: ליישר את מימוש דרישה 20 כך שיתאים ל-**Sequence Diagram** ול-**Class
Diagram** (תרשים 3) של חלק ב'. הגרסה הקודמת הפיקה ארבעה דוחות נפרדים (פרויקטים /
תשלומים / אבני דרך / התראות) ולא תאמה את התרשים שמתאר דוח ניהולי **מאוחד** מפרויקטים
פעילים.

## מה השתנה

1. **`ReportDashboardForm` כמחלקת User Class**
   - `views/report_dashboard.py` מומש מחדש כמחלקה (כמו `CustomerManagementForm`
     ו-`DecisionManagementForm`), עם השיטות `display_report_options`,
     `display_validation_error` ו-`display_management_report`.

2. **`ReportController` לפי הודעות התרשים**
   - נוספו השיטות התואמות ל-Sequence Diagram:
     `_validate_report_criteria`, `_get_active_projects`,
     `_get_milestones_status`, `_get_payment_requests`, `_get_project_alerts`,
     `_save_report`, והנקודה הציבורית `generate_management_report`.
   - בוטלה הגישה של ארבעה דוחות נפרדים (`generate_report(report_type)`).

3. **דוח ניהולי מאוחד מפרויקטים פעילים**
   - הדוח אוסף **רק** פרויקטים בסטטוס `Active`, ועליהם אבני דרך, דרישות תשלום
     (כולל סכום ששולם) והתראות. פרויקטים שהושלמו/בהמתנה אינם נכללים.

4. **מודל `Report` מורחב לפי תרשים המחלקות**
   - נוספו `criteria` ו-`status` (Enum `ReportStatus`: Requested/Generated/Saved),
     ושיטת `generate_management_report()` שמרכיבה את חלקי הדוח.

5. **שכבת Repository**
   - נוספו `find_active_projects`, `find_milestones_by_projects`,
     `find_payment_requests_by_projects`, `find_payments_by_requests`,
     `find_alerts_by_projects` ו-`save_report` (במקום `create_report`).

6. **בסיס נתונים**
   - טבלת `Reports` הורחבה בעמודות `criteria` ו-`status` (כולל migration
     ל-DB קיים).
   - נתוני ה-seed הועשרו: פרויקט פעיל שני (כדי שהדוח יאחד יותר מפרויקט אחד)
     ופרויקט שהושלם (כדי להדגים שהוא **אינו** נכלל בדוח).

7. **בדיקות**
   - נוספו/עודכנו בדיקות: הפקת דוח ניהולי, דחיית קריטריון חסר/לא מוכר, איסוף
     פרויקטים פעילים בלבד, ייצוא CSV, וחזרתיות (שתי הפקות → שתי רשומות היסטוריה).

## התאמות מול תרשים המחלקות (תרשים 3)

תרשים המחלקות של חלק ב' תיאר את `Milestone` עם `dueDate`/`amountDue` ואת
`PaymentRequest` עם `issueDate`. הסכמה במערכת שומרת את שדות הליבה בפועל
(`Milestone`: `title`, `status`; `PaymentRequest`: `amount`, `status`). אלו פרטי
מימוש שאינם משנים את זרימת ההודעות בדרישה 20; המיפוי המלא נמצא ב-
`requirement_20_code_diagram_mapping.md`.
