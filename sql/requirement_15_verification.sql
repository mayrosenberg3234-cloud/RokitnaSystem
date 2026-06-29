-- Requirement 15 — run after recording a professional decision.
-- The two queries prove that the decision and its audit entry were saved
-- together with user identity and second-level timestamps.

SELECT
    decisionId,
    projectId,
    createdByUserId,
    decisionText,
    createdAt
FROM DecisionLog
ORDER BY decisionId DESC;

SELECT
    changeId,
    projectId,
    decisionId,
    createdByUserId,
    description,
    createdAt
FROM ChangeHistory
ORDER BY changeId DESC;
