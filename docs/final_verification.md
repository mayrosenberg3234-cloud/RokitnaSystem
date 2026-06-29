# Final Verification — Requirements 1, 15 and 20

## Requirement 1 remains intact

- New projects linked from a digital client file always begin in `Active`.
- Client status cannot be changed manually through `update_client()`.
- A client with linked projects is archived through `Client.archive()` and then persisted by `DBRepository.archive_client()`.
- An archived client is read-only and cannot be updated, deleted again, linked to a new project, or used to update project progress.

## Requirement 15 additions

- Only an authenticated architect can record a professional decision.
- Decision text, actor identity and selected project are validated.
- Every decision is created with `projectId`, `createdByUserId` and `createdAt`.
- A matching `ChangeHistory` entry is created with `decisionId`, `projectId`, `createdByUserId` and `createdAt`.
- `save_decision_with_history()` uses one SQLite transaction. A failed history insert rolls back the decision insert, preventing partial data.
- The GUI displays both project decisions and the corresponding change history.
- `DecisionEntrySession` implements the states documented in the updated State Diagram.

## Requirement 20 alignment (Part C)

- The reporting flow now matches the Part B Sequence/Class Diagram: a single
  management report aggregated from the **active** projects.
- `ReportDashboardForm` is a real User Class; `ReportController` exposes the
  diagram methods (`validate_report_criteria`, `get_active_projects`,
  `get_milestones_status`, `get_payment_requests`, `get_project_alerts`,
  `generate_management_report`, `save_report`).
- Completed / on-hold projects are excluded; the generation is persisted in
  `Reports` with `criteria`, `status` and a second-level timestamp; CSV export
  produces a timestamped artefact.
- Full mapping: `docs/requirement_20_code_diagram_mapping.md`.

## Updated diagrams (colour-marked, Part C)

- Requirement 1: `docs/requirement_1_diagrams/` (State + Sequence).
- Requirement 15: `docs/requirement_15_diagrams/` (Class + Sequence + State).
- Requirement 20: code aligned to the Part B diagrams; deltas documented in
  `docs/requirement_20_changes.md`.

## Verification command

```bash
python -m unittest discover -s tests -v
```

## Result

58 automated tests passed successfully after the Requirement 20 alignment and
edge-case fixes.
