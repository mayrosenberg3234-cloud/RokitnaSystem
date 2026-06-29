# Requirement 1 — Project Linking Implementation

## Purpose

An authorised Office Manager can link a new project to a selected client from
the client's digital file. The implementation follows the business relation:

```text
Client 1 ---------------- 0..* Project
```

The link is stored in the database through `Projects.clientId`.

## Code Flow

```text
CustomerManagementForm._display_link_project_form()
  -> CustomerController.link_project_to_client()
      -> CustomerController._validate_project_details()
      -> DBRepository.get_client()
      -> <<create>> Project(client_id, project_name, ProjectStatus.ACTIVE)
      -> DBRepository.create_project()
  -> CustomerManagementForm refreshes the client file
  -> CustomerController.list_client_projects()
      -> DBRepository.list_projects_by_client()
```

## Business Rules

1. Only `OfficeManager` may link a project to a client.
2. The selected client must exist and be active.
3. Project name is mandatory.
4. A new project **always starts in `ProjectStatus.ACTIVE`**. The initial
   status is not accepted as external input, so the implementation cannot skip
   the initial state defined in the Project State Diagram.
5. The project is immediately visible in the digital client file.
6. Because a linked project preserves organisational history, a client with at
   least one linked project is archived rather than physically deleted.

## Diagram Updates Needed

### Class Diagram

Add to `CustomerController`:

```text
+linkProjectToClient(role:RoleEnum, clientId:int, projectName:String):ActionResult
-validateProjectDetails(projectName:String):String
```

Add to `CustomerManagementForm`:

```text
-displayLinkProjectForm(user:User, client:Client):void
```

Ensure `DBRepository` contains:

```text
+createProject(project:Project):int
```

### Sequence Diagram

Add a sequence path after the selected client is displayed:

```text
OfficeManager -> CustomerManagementForm: enterProjectName()
CustomerManagementForm -> CustomerController: linkProjectToClient(clientId, projectName)
CustomerController -> CustomerController: validateProjectDetails()
CustomerController -> DBRepository: getClient(clientId)
CustomerController -> Project: <<create>>(clientId, projectName, Active)
CustomerController -> DBRepository: createProject(project)
DBRepository --> CustomerController: projectId
CustomerController --> CustomerManagementForm: displaySuccessMessage()
CustomerManagementForm -> CustomerController: listClientProjects(clientId)
CustomerController -> DBRepository: listProjectsByClient(clientId)
```

### State Diagram

A new project begins at the initial project state:

```text
[Initial] -> ProjectActive
```

The client itself remains active, so retain the following self-transition:

```text
ClientActive -> ClientActive
linkProjectToClient() / createProject()
```
