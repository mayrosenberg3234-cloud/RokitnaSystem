from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages

OUT = Path(__file__).resolve().parent
plt.rcParams['font.family'] = 'DejaVu Sans'

participants = [
    'Architect:User',
    'DecisionManagementForm',
    'DecisionController',
    'DBRepository',
    'decision:DecisionLog',
    'history:ChangeHistory',
]
x = [0.7, 3.0, 5.6, 8.2, 10.8, 13.4]

fig, ax = plt.subplots(figsize=(18, 18))
ax.set_xlim(0, 14.2)
ax.set_ylim(0, 23)
ax.axis('off')
ax.set_title('Requirement 15 — Updated Sequence Diagram: Record Professional Decision', fontsize=17, pad=20)

# participant headers / lifelines
for xi, name in zip(x, participants):
    ax.add_patch(Rectangle((xi - 0.85, 21.9), 1.7, 0.55, facecolor='white', edgecolor='#2E7D32' if xi >= 3 else '#333333', linewidth=1.4))
    ax.text(xi, 22.18, name, ha='center', va='center', fontsize=9)
    ax.plot([xi, xi], [1.0, 21.9], linestyle=(0, (4, 3)), color='#777777', linewidth=0.8)

# helpers
def arrow(src, dst, y, label, dashed=False, color='#333333'):
    sx, dx = x[src], x[dst]
    patch = FancyArrowPatch(
        (sx, y), (dx, y), arrowstyle='->', mutation_scale=12,
        linewidth=1.2, linestyle='--' if dashed else '-', color=color,
    )
    ax.add_patch(patch)
    ax.text((sx + dx) / 2, y + 0.18, label, ha='center', va='bottom', fontsize=8, color=color,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none', alpha=0.85))

def self_arrow(idx, y, label):
    xi = x[idx]
    ax.plot([xi, xi+0.45, xi+0.45, xi], [y, y, y-0.48, y-0.48], color='#333333', linewidth=1.1)
    ax.annotate('', xy=(xi, y-0.48), xytext=(xi+0.03, y-0.48), arrowprops=dict(arrowstyle='->', lw=1.1))
    ax.text(xi+0.5, y-0.18, label, ha='left', va='center', fontsize=8)

def return_arrow(src, dst, y, label):
    arrow(src, dst, y, label, dashed=True, color='#555555')

# ref block
ax.add_patch(Rectangle((0.35, 20.75), 13.35, 0.65, facecolor='#F4FBF4', edgecolor='#2E7D32', linewidth=1.2))
ax.text(0.55, 21.08, 'ref LoginAndAuthentication  [authenticated architect]', ha='left', va='center', fontsize=9, color='#1B5E20')

# main sequence
arrow(0, 1, 19.95, '1. openDecisionForm()')
self_arrow(1, 19.45, '2. displayDecisionForm()')
arrow(0, 1, 18.55, '3. submitDecision(projectId, decisionText)')
arrow(1, 2, 17.85, '4. save_decision(role, userId, projectId, decisionText)', color='#2E7D32')
self_arrow(2, 17.2, '5. _validate_decision_details(decisionText)')

# alt validation
ax.add_patch(Rectangle((0.35, 14.7), 13.35, 1.8, fill=False, edgecolor='#555555', linewidth=1.1))
ax.text(0.5, 16.32, 'alt [decisionText missing / invalid actor]', ha='left', va='center', fontsize=9, weight='bold')
return_arrow(2, 1, 15.65, 'validationError')
self_arrow(1, 15.2, 'displayValidationError(message)')

# valid path
ax.add_patch(Rectangle((0.35, 3.0), 13.35, 11.1, fill=False, edgecolor='#2E7D32', linewidth=1.1))
ax.text(0.5, 13.9, 'else [details valid AND project exists]', ha='left', va='center', fontsize=9, weight='bold', color='#1B5E20')
arrow(2, 3, 13.2, '6. get_project(projectId)', color='#2E7D32')
return_arrow(3, 2, 12.7, '7. projectData')
arrow(2, 4, 12.05, '8. <<create>> DecisionLog(projectId, userId, text, createdAt)', color='#2E7D32')
arrow(2, 5, 11.4, '9. <<create>> ChangeHistory(projectId, decisionId, userId, description, createdAt)', color='#2E7D32')
arrow(2, 3, 10.65, '10. save_decision_with_history(decision, history)', color='#2E7D32')

# repository transaction note
ax.add_patch(Rectangle((7.1, 7.5), 2.2, 2.5, facecolor='#F4FBF4', edgecolor='#2E7D32', linewidth=1.0))
ax.text(8.2, 9.55, 'SQLite transaction', ha='center', va='center', fontsize=8, weight='bold', color='#1B5E20')
ax.text(8.2, 9.05, 'BEGIN', ha='center', va='center', fontsize=8)
ax.text(8.2, 8.55, 'INSERT DecisionLog', ha='center', va='center', fontsize=8)
ax.text(8.2, 8.05, 'INSERT ChangeHistory', ha='center', va='center', fontsize=8)
ax.text(8.2, 7.55, 'COMMIT / ROLLBACK', ha='center', va='center', fontsize=8)
return_arrow(3, 2, 7.0, '11. decisionId, changeId, timestamps')
return_arrow(2, 1, 6.35, '12. saveConfirmed')
self_arrow(1, 5.75, '13. displaySaveConfirmation()')
self_arrow(1, 5.15, '14. displayDecisions()')
self_arrow(1, 4.55, '15. displayChangeHistory()')

# failure note
ax.text(0.55, 2.25, 'alt [database save fails] → displaySaveError(); transaction rolls back; no partial records are kept', fontsize=8.5, color='#A33A3A')
ax.text(0.55, 1.55, 'Legend: dashed arrows = returned data / confirmation. Green = Part C additions and updated implementation.', fontsize=8, color='#555555')

png = OUT / 'Requirement15_SequenceDiagram_Updated.png'
pdf = OUT / 'Requirement15_SequenceDiagram_Updated.pdf'
fig.savefig(png, dpi=180, bbox_inches='tight')
fig.savefig(pdf, bbox_inches='tight')
plt.close(fig)
