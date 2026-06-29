# תרשימים מעודכנים — דרישה 1

בתיקייה זו נמצאים התרשימים המעודכנים של חלק ג' עבור דרישה 1 (ניהול תיק לקוח
דיגיטלי), המבוססים על הקוד שבמערכת בפועל.

## קבצים להגשה

* `Requirement1_UpdatedDiagrams_All.pdf` — שני התרשימים בקובץ PDF אחד.
* `Requirement1_StateDiagram_Updated.pdf` — State Diagram מעודכן.
* `Requirement1_SequenceDiagram_Updated.pdf` — Sequence Diagram מעודכן.

לכל תרשים קיים גם קובץ PNG. קובץ המקור הוא
`generate_requirement1_diagrams.py` (matplotlib).

## סימון חלק ג'

* **שחור** — רכיבים שהיו כבר בעיצוב חלק ב'.
* **ירוק** — תוספות/שינויים שנעשו בחלק ג' כדי לשמור על התאמה מלאה בין הקוד
  לבין התרשימים.

## השינויים העיקריים מול חלק ב'

1. **מחיקה מול ארכוב (שינוי מהותי).** בחלק ב' תרשים המצבים כלל את המצב
   `ClientDeletionBlocked` (ומסלול `can'tDeleteClient` / `displayDeleteError`
   בתרשים ה-Sequence) עבור לקוח עם פרויקטים פעילים. במימוש בפועל אין חסימת
   מחיקה: לקוח המקושר ל**כל** פרויקט (פעיל / בהמתנה / שהושלם) מועבר לארכיון,
   ולקוח ללא פרויקטים נמחק פיזית. המצב `ClientDeletionBlocked` הוסר.
2. **תיק לקוח דיגיטלי מלא (תוספת).** נוספו צפייה בלקוח בודד והצגת כל הפרויקטים
   המקושרים אליו (`get_client`, `list_client_projects`).
3. **קישור פרויקט ועדכון סטטוס (תוספת).** מתוך תיק הלקוח אפשר ליצור ולקשר
   פרויקט חדש (`link_project_to_client`) ולעדכן את סטטוס ההתקדמות שלו
   (`update_project_status`) לפי מחזור חיי הפרויקט.
4. **סטטוסי לקוח.** `ClientStatus` כולל בפועל שני מצבים נשמרים בלבד:
   `Active` ו-`Archived`. ולידציית הקלט מתבצעת באופן סינכרוני בקונטרולר, ולכן
   אין מצבי `Draft`/`PendingValidation` נשמרים בבסיס הנתונים.

המיפוי המלא message-אחר-message בין הקוד לתרשים נמצא בקובץ
`../requirement_1_code_diagram_mapping.md`.

## רינדור מחדש

```bash
python docs/requirement_1_diagrams/generate_requirement1_diagrams.py
```
(נדרש `matplotlib`.)
