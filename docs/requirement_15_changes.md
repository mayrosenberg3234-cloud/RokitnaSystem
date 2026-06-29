# דרישה 15 — שינויים שבוצעו בחלק ג'

## מה הושלם במימוש

1. `DecisionManagementForm` הפך למחלקת GUI אמיתית, בהתאם ל-Class Diagram.
2. נוספה הצגה של החלטות קודמות **וגם** היסטוריית שינויים לפרויקט שנבחר.
3. נוספה ישות זמנית `DecisionEntrySession` עם `DecisionEntryStatus`, כדי לממש בפועל את מחזור החיים המוצג ב-State Diagram.
4. `DecisionLog` שומר `created_by_user_id` ומקושר לפרויקט כבר בעת היצירה.
5. `ChangeHistory` שומר `decision_id`, `created_by_user_id`, `project_id`, תיאור וחותמת זמן.
6. נוספה בדיקת עקביות בין תפקיד המשתמש לבין מזהה המשתמש המחובר.
7. נוספה שמירה אטומית: החלטה והיסטוריה נשמרות באותה SQLite transaction.
8. נוספו מיגרציות למסד נתונים קיים, כך שהמערכת משדרגת את `rokitna.db` הישן בלי למחוק נתונים.
9. נוספו בדיקות הרשאה, ולידציה, קישור משתמש, קישור החלטה-היסטוריה, rollback ו-State Diagram.

## מה לא שונה

* דרישה 1 נשארה ללא שינוי: ניהול לקוחות, קישור פרויקט ללקוח ועדכון סטטוס פרויקט ממשיכים לפעול כפי שמומשו.
* דרישה 20 נשארה ללא שינוי: דוחות וייצוא CSV לא נפגעו.
* מנגנון Login והרשאות הקיים נשמר; דרישה 15 משתמשת בו באמצעות `RoleEnum.ARCHITECT` ו-`Permission.RECORD_DECISIONS`.

## נתונים שצריך להראות בהצגה

לאחר שמירת החלטה, הציגי במסך את טבלת ההחלטות ואת טבלת היסטוריית השינויים. אפשר גם להפעיל ב-SQLite את השאילתות:

```sql
SELECT decisionId, projectId, createdByUserId, decisionText, createdAt
FROM DecisionLog
ORDER BY decisionId DESC;

SELECT changeId, projectId, decisionId, createdByUserId, description, createdAt
FROM ChangeHistory
ORDER BY changeId DESC;
```

הצגת `decisionId`, `createdByUserId` ו-`createdAt` מוכיחה שההחלטה נשמרה לפרויקט הנכון, תועדה על ידי משתמש מזוהה ונוספה בזמן אמת להיסטוריה.
