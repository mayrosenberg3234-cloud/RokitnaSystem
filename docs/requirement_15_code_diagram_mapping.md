# דרישה 15 — מיפוי מלא בין קוד, Class Diagram, Sequence Diagram ו-State Diagram

## הדרישה העסקית
האדריכלית מתעדת החלטה מקצועית עבור פרויקט קיים. המערכת בודקת הרשאה ותקינות, יוצרת החלטה המקושרת לפרויקט, שומרת בו-זמנית רשומת `ChangeHistory`, ומציגה לאחר השמירה הן את רשימת ההחלטות והן את היסטוריית השינויים.

## מיפוי Class Diagram → קוד

| אלמנט בתרשים | מיקום בקוד | אחריות |
|---|---|---|
| `User` | `models/user.py` | משתמש מחובר; מזהה, תפקיד וסטטוס פעילות. |
| `RoleEnum` | `models/user.py` | תפקידי המערכת: מנהל משרד, אדריכלית, לקוח. |
| `Project` | `models/project.py` | הפרויקט שאליו ההחלטה משויכת באמצעות `project_id`. |
| `DecisionLog` | `models/decision_log.py` | ישות עסקית מתמשכת: תוכן החלטה, פרויקט, מתעד וחותמת זמן. |
| `ChangeHistory` | `models/change_history.py` | רשומת ביקורת מתמשכת: פרויקט, החלטה, מתעד, תיאור וחותמת זמן. |
| `DecisionEntrySession` | `models/decision_entry_session.py` | אובייקט זמני למימוש State Diagram של תהליך הזנת החלטה. |
| `DecisionEntryStatus` | `models/decision_entry_session.py` | המצבים Draft, Invalid, Saving, Recorded, SaveFailed, Closed. |
| `DecisionManagementForm` | `views/decision_management.py` | מחלקת GUI: קלט, הצגה, הודעות משוב ורשימות. |
| `DecisionController` | `controllers/decision_controller.py` | הרשאות, ולידציה, יצירת אובייקטים ותיאום תהליך. |
| `DBRepository` | `repositories/db_repository.py` | שכבת הגישה היחידה ל-SQL ולשמירה אטומית. |

## מיפוי Sequence Diagram → קוד

| # | Message בתרשים | Method בקוד | קובץ |
|---:|---|---|---|
| 1 | `ref LoginAndAuthentication` | `AuthController.login()` | `controllers/auth_controller.py` |
| 2 | `openDecisionForm()` | `DecisionManagementForm.render()` | `views/decision_management.py` |
| 3 | `displayDecisionForm()` | `DecisionManagementForm.display_decision_form()` | `views/decision_management.py` |
| 4 | `submitDecision(...)` | `DecisionManagementForm.display_decision_form()` | `views/decision_management.py` |
| 5 | `save_decision(role,userId,projectId,text)` | `DecisionController.save_decision()` | `controllers/decision_controller.py` |
| 6 | `validateDecisionDetails(text)` | `DecisionController._validate_decision_details()` | `controllers/decision_controller.py` |
| 7 | `getProject(projectId)` | `DBRepository.get_project()` | `repositories/db_repository.py` |
| 8 | `<<create>> DecisionLog` | `DecisionLog(...)` | `controllers/decision_controller.py` |
| 9 | `<<create>> ChangeHistory` | `ChangeHistory(...)` | `controllers/decision_controller.py` |
| 10 | `saveDecisionWithHistory(decision,history)` | `DBRepository.save_decision_with_history()` | `repositories/db_repository.py` |
| 11 | `displaySaveConfirmation()` | `DecisionManagementForm.display_save_confirmation()` | `views/decision_management.py` |
| 12 | `displayDecisions()` | `DecisionManagementForm.display_decisions()` | `views/decision_management.py` |
| 13 | `displayChangeHistory()` | `DecisionManagementForm.display_change_history()` | `views/decision_management.py` |
| 14 | `displayValidationError()` | `DecisionManagementForm.display_validation_error()` | `views/decision_management.py` |
| 15 | `displaySaveError()` | `DecisionManagementForm.display_save_error()` | `views/decision_management.py` |

## מיפוי State Diagram → קוד

| מצב | ייצוג בקוד | מעבר |
|---|---|---|
| `DecisionDraft` | `DecisionEntryStatus.DRAFT` | פתיחת טופס / תיקון פרטים |
| `DecisionInvalid` | `DecisionEntryStatus.INVALID` | טקסט ריק, פרויקט לא נמצא או זהות לא תקינה |
| `DecisionSaving` | `DecisionEntryStatus.SAVING` | התחלת `save_decision()` |
| `DecisionRecorded` | `DecisionEntryStatus.RECORDED` | `save_decision_with_history()` הסתיימה ב-commit |
| `DecisionSaveFailed` | `DecisionEntryStatus.SAVE_FAILED` | כשל SQL; הטרנזקציה בוצעה rollback |
| `DecisionClosed` | `DecisionEntryStatus.CLOSED` | לחיצה על “סיום תיעוד החלטה” |

## כלל עסקי מרכזי: שמירה אטומית
`DBRepository.save_decision_with_history()` מכניסה את ההחלטה ואת רשומת ההיסטוריה לאותה transaction. אם פעולת שמירת ההיסטוריה נכשלת, הטרנזקציה כולה מתבטלת. לכן לא ייתכן מצב שבו נשמרת החלטה ללא תיעוד בהיסטוריית הפרויקט.
