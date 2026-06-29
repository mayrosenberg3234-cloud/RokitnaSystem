# דרישה 1 — מיפוי מלא בין התרשימים לקוד

מסמך זה נועד להצגה בכיתה ולתיקון התרשימים של חלק ג'. הוא מתאר את **הקוד בפועל** לאחר התיקון.  
כל שם שמופיע כאן תואם לשם מחלקה או שיטה בקוד; בקוד Python השמות נכתבים ב־`snake_case`.

## 1. החלטה עסקית מרכזית

לקוח שמקושר לפרויקט כלשהו **אינו נמחק פיזית** — גם אם הפרויקט הושלם או נמצא בהמתנה. במקום מחיקה הוא מועבר לסטטוס `Archived`.

הסיבה: הפרויקט הוא חלק מהזיכרון הארגוני של Rokitna, וכל פרויקט מחזיק `clientId` של לקוח אחד. מחיקה של הלקוח תפגע בהיסטוריית הפרויקטים ואף עלולה להפר שלמות קשרי Foreign Key במסד הנתונים.

---

## 2. Class Diagram — מה צריך להופיע

### `CustomerManagementForm` — User Class

```text
CustomerManagementForm
+render(user:User):void
-displayCreateForm(user:User):void
-displayClientsTable(user:User):void
-displayClientDetails(user:User, client:Client):void
-displayLinkProjectForm(user:User, client:Client):void
-displayProjectStatusUpdateForm(user:User, client:Client, projects:List<Project>):void
-displayEditSection(user:User, clients:List<Client>):void
-displayDeleteConfirmation(user:User, client:Client):void
```

### `CustomerController` — Controller / System Class

```text
CustomerController
-repository:DBRepository

+listClients(role:RoleEnum):ActionResult
+getClient(role:RoleEnum, clientId:int):ActionResult
+listClientProjects(role:RoleEnum, clientId:int):ActionResult
+linkProjectToClient(role:RoleEnum, clientId:int, projectName:String):ActionResult
+updateProjectStatus(role:RoleEnum, clientId:int, projectId:int, newStatus:ProjectStatus):ActionResult
+createClient(role:RoleEnum, name:String, phone:String, email:String):ActionResult
+updateClient(role:RoleEnum, clientId:int, name:String, phone:String, email:String):ActionResult
+deleteClient(role:RoleEnum, clientId:int):ActionResult

-validateClientDetails(name:String, phone:String, email:String)
-checkDuplicateClient(phone:String, email:String, excludedClientId:int)
-checkClientProjects(clientId:int):int
-validateProjectDetails(projectName:String):String
-validateProjectStatusTransition(project:Project, newStatus:ProjectStatus):String
```

### `Client` — Business Class

```text
Client
-clientId:int
-name:String
-phone:String
-email:String
-status:ClientStatus
-createdAt:DateTime
-updatedAt:DateTime

+archive():void
```

### `Project` — Business Class

```text
Project
-projectId:int
-clientId:int
-projectName:String
-status:ProjectStatus
-createdAt:DateTime
-updatedAt:DateTime

+availableNextStatuses():List<ProjectStatus>
+canTransitionTo(newStatus:ProjectStatus):Boolean
+updateProjectStatus(newStatus:ProjectStatus):void
```

### `DBRepository` — System Class / Data Access Layer

```text
DBRepository
+listClients():List<Client>
+getClient(clientId:int):Client
+findClientByPhone(phone:String):Client
+findClientByEmail(email:String):Client
+createClient(client:Client):int
+updateClient(client:Client):void
+deleteClient(clientId:int):void
+archiveClient(clientId:int):void
+countProjectsForClient(clientId:int):int
+listProjectsByClient(clientId:int):List<Project>
+createProject(project:Project):int
+getProject(projectId:int):Project
+updateProjectStatus(projectId:int, newStatus:ProjectStatus):Boolean
```

### Enumerations

```text
<<enumeration>>
ClientStatus
Active
Archived

<<enumeration>>
ProjectStatus
Active
Completed
OnHold
```

### קשרים בתרשים

```text
CustomerManagementForm  - - - - >  CustomerController  - - - - >  DBRepository
CustomerController      - - - - >  Client : <<create>>
CustomerController      - - - - >  Project : <<create>>
Client  1  -----------------------  0..* Project
```

אין קרדינליות על חצי Dependency. הקרדינליות `1` מול `0..*` מופיעה רק על הקשר העסקי הקבוע בין `Client` ל־`Project`.

## 3. Sequence Diagram — מיפוי message אחר message

### 3.1 יצירת לקוח

| שלב לוגי ב־Sequence | המחלקה / השיטה בקוד | קובץ |
|---|---|---|
| פתיחת מסך ניהול לקוחות | `CustomerManagementForm.render()` | `views/customer_management.py` |
| הזנת פרטים ולחיצה על יצירה | `_display_create_form()` | `views/customer_management.py` |
| יצירת לקוח | `CustomerController.create_client()` | `controllers/customer_controller.py` |
| ולידציה פנימית | `CustomerController._validate_client_details()` | `controllers/customer_controller.py` |
| בדיקת כפילות פנימית | `CustomerController._check_duplicate_client()` | `controllers/customer_controller.py` |
| יצירת מופע לקוח | `Client(name, phone, email)` | `controllers/customer_controller.py` |
| שמירה | `DBRepository.create_client()` | `repositories/db_repository.py` |
| משוב למשתמש | `_set_feedback()` ואז `_display_pending_feedback()` | `views/customer_management.py` |

### 3.2 צפייה בתיק לקוח ובפרויקטים מקושרים

| שלב לוגי ב־Sequence | המחלקה / השיטה בקוד | קובץ |
|---|---|---|
| הצגת רשימת לקוחות | `CustomerController.list_clients()` | `controllers/customer_controller.py` |
| שליפת לקוח נבחר | `CustomerController.get_client()` | `controllers/customer_controller.py` |
| אחזור לקוח | `DBRepository.get_client()` | `repositories/db_repository.py` |
| הצגת תיק לקוח | `CustomerManagementForm._display_client_details()` | `views/customer_management.py` |
| אחזור פרויקטים מקושרים | `CustomerController.list_client_projects()` | `controllers/customer_controller.py` |
| שליפת פרויקטים | `DBRepository.list_projects_by_client()` | `repositories/db_repository.py` |

### 3.3 קישור פרויקט ללקוח

| שלב לוגי ב־Sequence | המחלקה / השיטה בקוד | קובץ |
|---|---|---|
| בחירת לקוח בתיק הלקוח | `_display_edit_section()` | `views/customer_management.py` |
| פתיחת טופס קישור פרויקט | `CustomerManagementForm._display_link_project_form()` | `views/customer_management.py` |
| בקשת קישור פרויקט | `CustomerController.link_project_to_client()` | `controllers/customer_controller.py` |
| ולידציית שם הפרויקט | `CustomerController._validate_project_details()` | `controllers/customer_controller.py` |
| אימות לקוח פעיל | `DBRepository.get_client()` + בדיקת `ClientStatus.ACTIVE` | `controllers/customer_controller.py` |
| יצירת מופע פרויקט | `Project(client_id, project_name, status)` | `controllers/customer_controller.py` |
| שמירת הקשר | `DBRepository.create_project()` — שומר `clientId` בטבלת `Projects` | `repositories/db_repository.py` |
| הצגת פרויקט מקושר | `DBRepository.list_projects_by_client()` | `repositories/db_repository.py` |

הקשר מיושם בפועל דרך `Projects.clientId`. לכן לכל פרויקט יש לקוח אחד בדיוק, וללקוח יכולים להיות אפס או יותר פרויקטים.

### 3.4 עדכון לקוח

| שלב לוגי ב־Sequence | המחלקה / השיטה בקוד | קובץ |
|---|---|---|
| שליחת בקשת עדכון | `CustomerController.update_client()` | `controllers/customer_controller.py` |
| ולידציה | `_validate_client_details()` | `controllers/customer_controller.py` |
| קבלת הלקוח הקיים | `DBRepository.get_client()` | `repositories/db_repository.py` |
| בדיקת כפילות ללא הלקוח עצמו | `_check_duplicate_client(..., excluded_client_id=client_id)` | `controllers/customer_controller.py` |
| שמירה ועדכון חותמת זמן | `DBRepository.update_client()` | `repositories/db_repository.py` |

### 3.5 מחיקה או ארכוב

יש להשתמש ב־`alt` בתרשים:

```text
alt [project_count > 0]
    archive_client(client_id)
    display archived message
else [project_count = 0]
    delete_client(client_id)
    display deleted message
```

| שלב לוגי ב־Sequence | המחלקה / השיטה בקוד | קובץ |
|---|---|---|
| בקשת מחיקה | `_display_edit_section()` | `views/customer_management.py` |
| אישור משתמש | `_display_delete_confirmation()` | `views/customer_management.py` |
| בדיקת קיום לקוח | `DBRepository.get_client()` | `repositories/db_repository.py` |
| בדיקת פרויקטים מקושרים | `CustomerController._check_client_projects()` | `controllers/customer_controller.py` |
| ספירת פרויקטים מכל סטטוס | `DBRepository.count_projects_for_client()` | `repositories/db_repository.py` |
| ארכוב | `DBRepository.archive_client()` | `repositories/db_repository.py` |
| מחיקה | `DBRepository.delete_client()` | `repositories/db_repository.py` |

---

## 4. State Diagram — התאמה למימוש

אלו המצבים והמעברים שהקוד מממש בפועל:

```text
● -> ClientActive : create_client()

ClientActive -> ClientActive : update_client()

ClientActive -> ClientActive : link_project_to_client()
do / create_project()

ClientActive -> ClientArchived
delete_client() [count_projects_for_client(client_id) > 0]
entry / archive()

do / DBRepository.archive_client(clientId)

ClientActive -> ◎
delete_client() [count_projects_for_client(client_id) = 0]
entry / delete_client(client_id)
```

### דגש חשוב

- `ClientDeleted` אינו Enum ולא רשומה נשמרת: הוא מצב סופי, כי הלקוח נמחק פיזית מבסיס הנתונים.
- המסך אינו מאפשר שינוי ידני של `ClientStatus`, כדי לא ליצור מעבר לא מתועד כגון `Archived -> Active`.
- `created_at` ו־`updated_at` מוצגים בממשק, ולכן אפשר להראות בהדגמה שהפעולה נשמרה בזמן אמת.

---

## 5. תרחיש הדגמה מומלץ

1. התחברי כ־`manager` / `1234`.
2. צרי לקוח חדש והציגי את רשימת הלקוחות כולל `created_at`.
3. בחרי את הלקוח, הציגי את תיק הלקוח הדיגיטלי.
4. עדכני פרטי קשר והציגי `updated_at`.
5. בתיק הלקוח הזיני שם פרויקט ולחצי **קשר פרויקט ללקוח**. הציגי שהפרויקט החדש מופיע מיד ברשימת הפרויקטים המקושרים.
6. לחצי **בקשת מחיקה** ולאחר מכן **אישור מחיקה**.
7. הציגי שהלקוח הועבר לסטטוס "בארכיון" ולא נמחק, מפני שיש פרויקט מקושר.
8. הראי בקוד את הרצף: `delete_client()` → `_check_client_projects()` → `count_projects_for_client()` → `Client.archive()` → `DBRepository.archive_client()`.
