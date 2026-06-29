# Requirement 1 — Final Code Alignment

This document records the final code-level safeguards added to ensure that the
digital client-file implementation follows the approved Class, Sequence and
State Diagrams.

## Client lifecycle

- A new client is created in `ClientStatus.ACTIVE`.
- Client details can be updated only while the client is active.
- When deletion is requested:
  - no linked projects -> the client is permanently deleted;
  - one or more linked projects -> `Client.archive()` changes the domain
    object to `Archived`, and `DBRepository.archive_client()` persists the
    transition.
- An archived client is displayed as read-only. It cannot be updated, deleted
  again, linked to a new project or used to update project progress.

## Project lifecycle

- `link_project_to_client()` always creates the new `Project` in the initial
  state `ProjectStatus.ACTIVE`.
- Later transitions are performed only through `update_project_status()`: 
  `Active -> OnHold/Completed`, `OnHold -> Active/Completed`.
- `Completed` is terminal in the standard workflow.

## Presentation mapping

For Requirement 1, show the following code sequence during the live mapping:

1. `CustomerManagementForm` calls `CustomerController.link_project_to_client()`.
2. The controller validates the project name and selected active client.
3. The controller creates `Project(..., status=ProjectStatus.ACTIVE)`.
4. `DBRepository.create_project()` stores the mandatory `clientId` link.
5. The client file refreshes and displays the linked project and its timestamps.

For client archiving, show:

1. `CustomerManagementForm` asks for deletion confirmation.
2. `CustomerController.delete_client()` calls `_check_client_projects()`.
3. When projects exist, `Client.archive()` performs the business state change.
4. `DBRepository.archive_client()` persists the state and timestamp.
