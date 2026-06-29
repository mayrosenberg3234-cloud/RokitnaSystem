# Requirement 1 — Project Status Update by Client

## Purpose

The digital client file now allows the Office Manager to update the status of a
project that is already linked to the selected client. The feature represents
project progress while preserving ownership, permissions, database integrity and
the project lifecycle defined in the State Diagram.

## Business rules implemented

1. Only `OfficeManager` can update a project's status.
2. The selected client must exist and must not be archived.
3. The selected project must belong to the selected client.
4. A newly linked project is created in `Active` status.
5. Valid lifecycle transitions are:

   ```text
   Active  -> OnHold
   Active  -> Completed
   OnHold  -> Active
   OnHold  -> Completed
   Completed -> no further transition
   ```

6. Updating a project refreshes `Projects.updatedAt` with a timestamp to the
   second.
7. Invalid input, a wrong client-project relation, lack of permission, an
   archived client, an identical status, or an invalid lifecycle transition
   return a friendly Hebrew message rather than a technical error.

## Code mapping — Class Diagram

### `Project` (Business Class)

```text
Project
-clientId:int
-projectId:int
-projectName:String
-status:ProjectStatus
-createdAt:DateTime
-updatedAt:DateTime

+availableNextStatuses():List<ProjectStatus>
+canTransitionTo(newStatus:ProjectStatus):Boolean
+updateProjectStatus(newStatus:ProjectStatus):void
```

Code: `models/project.py`

### `CustomerController` (System / Controller Class)

```text
+updateProjectStatus(
  role:RoleEnum,
  clientId:int,
  projectId:int,
  newStatus:ProjectStatus
):ActionResult

-validateProjectStatusTransition(
  project:Project,
  newStatus:ProjectStatus
):String
```

Code: `controllers/customer_controller.py`

### `DBRepository` (System Class)

```text
+getProject(projectId:int):Project
+updateProjectStatus(projectId:int, newStatus:ProjectStatus):Boolean
+listProjectsByClient(clientId:int):List<Project>
```

Code: `repositories/db_repository.py`

### `CustomerManagementForm` (User Class)

```text
-displayProjectStatusUpdateForm(user:User, client:Client, projects:List<Project>):void
```

Code: `views/customer_management.py`

## Code mapping — Sequence Diagram

Add this flow inside the existing Requirement 1 Sequence Diagram after the
linked-projects display:

```text
OfficeManager -> CustomerManagementForm:
selectProjectForStatusUpdate()

CustomerManagementForm -> CustomerController:
updateProjectStatus(role, clientId, projectId, newStatus)

CustomerController -> CustomerController:
validateProjectStatusTransition(project, newStatus)

CustomerController -> DBRepository:
getClient(clientId)

CustomerController -> DBRepository:
getProject(projectId)

CustomerController -> Project:
canTransitionTo(newStatus)

CustomerController -> Project:
updateProjectStatus(newStatus)

CustomerController -> DBRepository:
updateProjectStatus(projectId, newStatus)

DBRepository --> CustomerController:
updatedProject

CustomerController --> CustomerManagementForm:
statusUpdateConfirmation(updatedProject)

CustomerManagementForm -> CustomerManagementForm:
displaySuccessMessage()
```

### `alt` fragments required in the Sequence Diagram

```text
alt [Project does not belong to selected Client]
    CustomerManagementForm <- CustomerController: displayValidationError()
else [Client is archived]
    CustomerManagementForm <- CustomerController: displayValidationError()
else [Invalid status transition]
    CustomerManagementForm <- CustomerController: displayValidationError()
else [User lacks permission]
    CustomerManagementForm <- CustomerController: displayPermissionError()
else [Valid transition]
    DBRepository updates Projects.status and Projects.updatedAt
    CustomerManagementForm displays a success message
end
```

## Code mapping — State Diagram

Create or update a Project State Diagram with the following states and
transitions:

```text
[Initial] -> ProjectActive

ProjectActive -- updateProjectStatus(OnHold) --> ProjectOnHold
ProjectActive -- updateProjectStatus(Completed) --> ProjectCompleted

ProjectOnHold -- updateProjectStatus(Active) --> ProjectActive
ProjectOnHold -- updateProjectStatus(Completed) --> ProjectCompleted

ProjectCompleted [final business state]
```

Recommended actions inside the states:

```text
ProjectActive
entry / setProjectStatus(Active)

ProjectOnHold
entry / setProjectStatus(OnHold)

ProjectCompleted
entry / setProjectStatus(Completed)
```

In the code, the state change is implemented by
`Project.update_project_status(new_status)` and persisted through
`DBRepository.update_project_status(...)`.

## Live demonstration script

1. Log in as `manager` / `1234`.
2. Open **ניהול לקוחות**.
3. Select a client with a linked active project.
4. In **עדכון סטטוס פרויקט לפי התקדמות**, choose the project.
5. Change it from **פעיל** to **בהמתנה** or **הושלם**.
6. Show that the project table refreshes with the new status and `עודכן בתאריך`.
7. Attempt an invalid action, such as reopening a completed project, to show a
   clear validation message.
8. Optionally show the SQL proof:

   ```sql
   SELECT projectId, clientId, projectName, status, createdAt, updatedAt
   FROM Projects
   WHERE clientId = <selected client id>;
   ```

## Tests added

The automated test suite verifies:

- manager can update a linked project's status;
- manager can resume an OnHold project;
- manager can complete an Active project;
- a Completed project cannot be reopened;
- a project belonging to another client cannot be updated from this client file;
- an Architect cannot update project progress;
- an archived client cannot update project progress;
- an identical status update is rejected.
