"""Generate the updated Requirement 1 diagrams (Part C).

Produces, from the actual implemented code:
  * Requirement1_StateDiagram_Updated.(png|pdf)
  * Requirement1_SequenceDiagram_Updated.(png|pdf)
  * Requirement1_UpdatedDiagrams_All.pdf  (both, one per page)

Colour convention (same as the Requirement 15 diagrams):
  * BLACK  — elements that already existed in the Part B design.
  * GREEN  — additions / changes introduced in Part C so the diagram matches
             the real system (digital-file viewing, project linking, project
             status updates, and archive-instead-of-block on delete).

Run:  python generate_requirement1_diagrams.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages

OUT = Path(__file__).resolve().parent
plt.rcParams["font.family"] = "DejaVu Sans"

BLACK = "#222222"
GREEN = "#2E7D32"
GREEN_FILL = "#F4FBF4"
GRAY = "#777777"


# --------------------------------------------------------------------------- #
# State diagram
# --------------------------------------------------------------------------- #
def build_state_diagram():
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.axis("off")
    ax.set_title(
        "Requirement 1 — Updated State Diagram: Digital Client File",
        fontsize=15,
        pad=16,
    )

    def state(x, y, w, h, title, lines, color=BLACK, fill="#FFFFFF"):
        box = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=1.6,
            edgecolor=color,
            facecolor=fill,
        )
        ax.add_patch(box)
        ax.text(
            x + w / 2,
            y + h - 0.28,
            title,
            ha="center",
            va="center",
            fontsize=10.5,
            weight="bold",
            color=color,
        )
        ax.plot([x + 0.15, x + w - 0.15], [y + h - 0.5, y + h - 0.5], color=color, lw=0.8)
        ax.text(
            x + w / 2,
            y + (h - 0.5) / 2,
            "\n".join(lines),
            ha="center",
            va="center",
            fontsize=8.2,
            color="#333333",
        )

    def edge(p1, p2, label, color=BLACK, rad=0.0, lx=None, ly=None):
        ax.add_patch(
            FancyArrowPatch(
                p1,
                p2,
                arrowstyle="-|>",
                mutation_scale=14,
                lw=1.3,
                color=color,
                connectionstyle=f"arc3,rad={rad}",
            )
        )
        if label:
            mx = lx if lx is not None else (p1[0] + p2[0]) / 2
            my = ly if ly is not None else (p1[1] + p2[1]) / 2
            ax.text(
                mx,
                my,
                label,
                ha="center",
                va="center",
                fontsize=8,
                color=color,
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white", edgecolor="none", alpha=0.9),
            )

    # initial node
    ax.add_patch(plt.Circle((1.0, 7.9), 0.12, color=BLACK))
    # final nodes
    ax.add_patch(plt.Circle((6.4, 0.7), 0.18, fill=False, color=BLACK, lw=1.4))
    ax.add_patch(plt.Circle((6.4, 0.7), 0.09, color=BLACK))
    ax.add_patch(plt.Circle((11.7, 2.2), 0.18, fill=False, color=BLACK, lw=1.4))
    ax.add_patch(plt.Circle((11.7, 2.2), 0.09, color=BLACK))

    # States
    state(3.7, 4.5, 4.0, 2.4, "ClientActive",
          ["entry / setClientStatus(\"Active\")",
           "do / display_client_file()",
           "",
           "self: update_client()",
           "self: link_project_to_client()  [Part C]",
           "self: update_project_status()  [Part C]"])
    state(8.7, 4.7, 3.9, 1.8, "ClientArchived",
          ["entry / Client.archive()",
           "do / archive_client()",
           "read-only (no update / re-delete /",
           "new project / status change)"], color=GREEN, fill=GREEN_FILL)

    # transitions
    edge((1.0, 7.78), (4.6, 6.9), "createClientRequest [valid & not duplicate]\n/ create_client()",
         color=GREEN, lx=2.7, ly=7.7)
    edge((7.7, 5.9), (8.7, 5.7), "deleteClient\n[linked projects exist]",
         color=GREEN, lx=8.2, ly=6.35)
    edge((5.0, 4.5), (6.4, 0.9), "deleteClient [no linked projects]\n/ delete_client()",
         color=BLACK, rad=-0.15, lx=4.0, ly=2.4)
    edge((10.6, 4.7), (11.7, 2.4), "removeClientPermanently", color=BLACK, rad=-0.2,
         lx=11.9, ly=3.6)

    # Part C note
    note = FancyBboxPatch(
        (0.4, 0.5), 3.4, 2.0,
        boxstyle="round,pad=0.1,rounding_size=0.08",
        linewidth=1.2, edgecolor=GREEN, facecolor=GREEN_FILL,
    )
    ax.add_patch(note)
    ax.text(
        2.1, 1.5,
        "Part C change\n\nPart B state 'ClientDeletionBlocked'\n(displayDeleteError / can'tDeleteClient)\nis REMOVED. A client linked to ANY\nproject (Active/OnHold/Completed) is\narchived, not blocked. Persisted\nClientStatus = { Active, Archived }.",
        ha="center", va="center", fontsize=7.6, color=GREEN,
    )

    ax.text(8.6, 0.4, "GREEN = Part C additions / changes vs Part B",
            ha="left", va="center", fontsize=8, color=GREEN)
    return fig


# --------------------------------------------------------------------------- #
# Sequence diagram
# --------------------------------------------------------------------------- #
def build_sequence_diagram():
    participants = [
        "OfficeManager:User",
        "CustomerManagementForm",
        "CustomerController",
        "Client / Project",
        "DBRepository",
    ]
    x = [0.9, 3.6, 6.6, 9.6, 12.2]

    fig, ax = plt.subplots(figsize=(15, 19))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 27)
    ax.axis("off")
    ax.set_title(
        "Requirement 1 — Updated Sequence Diagram: Digital Client File (CRUD + link + status)",
        fontsize=14,
        pad=18,
    )

    for xi, name in zip(x, participants):
        green = xi >= 9.6 - 0.01 and False  # all headers black; controllers neutral
        ax.add_patch(Rectangle((xi - 1.05, 25.9), 2.1, 0.5, facecolor="white", edgecolor=BLACK, lw=1.3))
        ax.text(xi, 26.15, name, ha="center", va="center", fontsize=8.6)
        ax.plot([xi, xi], [0.6, 25.9], linestyle=(0, (4, 3)), color=GRAY, lw=0.8)

    def arrow(src, dst, y, label, dashed=False, color=BLACK):
        ax.add_patch(FancyArrowPatch((x[src], y), (x[dst], y), arrowstyle="->",
                                     mutation_scale=12, lw=1.15,
                                     linestyle="--" if dashed else "-", color=color))
        ax.text((x[src] + x[dst]) / 2, y + 0.16, label, ha="center", va="bottom",
                fontsize=7.8, color=color,
                bbox=dict(boxstyle="round,pad=0.14", facecolor="white", edgecolor="none", alpha=0.88))

    def self_arrow(idx, y, label, color=BLACK):
        xi = x[idx]
        ax.plot([xi, xi + 0.4, xi + 0.4, xi], [y, y, y - 0.42, y - 0.42], color=color, lw=1.0)
        ax.annotate("", xy=(xi, y - 0.42), xytext=(xi + 0.04, y - 0.42),
                    arrowprops=dict(arrowstyle="->", lw=1.0, color=color))
        ax.text(xi + 0.46, y - 0.18, label, ha="left", va="center", fontsize=7.8, color=color)

    def ret(src, dst, y, label):
        arrow(src, dst, y, label, dashed=True, color="#555555")

    def frame(y0, y1, label, color=BLACK):
        ax.add_patch(Rectangle((0.35, y0), 12.5, y1 - y0, fill=False, edgecolor=color, lw=1.1))
        ax.text(0.5, y1 - 0.25, label, ha="left", va="center", fontsize=8.6, weight="bold", color=color)

    # ref
    ax.add_patch(Rectangle((0.35, 25.0), 12.5, 0.6, facecolor=GREEN_FILL, edgecolor=GREEN, lw=1.1))
    ax.text(0.5, 25.3, "ref  LoginAndAuthentication  [authenticated office manager]",
            ha="left", va="center", fontsize=8.5, color=GREEN)

    arrow(0, 1, 24.5, "1. openCustomerManagementForm()")
    self_arrow(1, 24.0, "2. displayCustomerManagementOptions()")
    arrow(0, 1, 23.2, "3. selectAction(create / view / update / delete)")

    # CREATE
    frame(17.7, 22.8, "alt  [Create]")
    arrow(0, 1, 22.2, "4. insertClientDetails(name, phone, email)")
    arrow(1, 2, 21.6, "5. create_client(role, name, phone, email)", color=GREEN)
    self_arrow(2, 21.1, "6. _validate_client_details()")
    self_arrow(2, 20.4, "7. _check_duplicate_client(phone, email)")
    arrow(2, 4, 19.85, "8. find_client_by_phone / by_email()")
    ax.text(x[4], 19.5, "(DBRepository -> Clients)", ha="center", fontsize=7, color=GRAY)
    arrow(2, 3, 19.0, "9. <<create>> Client")
    arrow(2, 4, 18.45, "10. create_client(client)")
    ret(2, 1, 18.05, "11. clientCreated")

    # VIEW
    frame(13.9, 17.4, "alt  [View digital client file]   (Part C: full file + projects)", color=GREEN)
    self_arrow(1, 17.0, "12. displaySuccessMessage / displayDuplicateError / displayValidationError")
    arrow(1, 2, 16.4, "13. get_client(role, clientId)", color=GREEN)
    arrow(2, 4, 15.85, "14. get_client(clientId)")
    ret(4, 2, 15.45, "clientData")
    arrow(1, 2, 15.0, "15. list_client_projects(role, clientId)", color=GREEN)
    arrow(2, 4, 14.5, "16. list_projects_by_client(clientId)")
    self_arrow(1, 14.3, "17. displayClientDetails()  [+ linked projects]", color=GREEN)

    # LINK + STATUS (Part C)
    frame(11.2, 14.3, "alt  [Link project / update status]   (Part C addition)", color=GREEN)
    arrow(1, 2, 13.7, "18. link_project_to_client(role, clientId, projectName)", color=GREEN)
    arrow(2, 3, 13.15, "19. <<create>> Project(status=Active)", color=GREEN)
    arrow(2, 4, 12.6, "20. create_project(project)", color=GREEN)
    arrow(1, 2, 12.05, "21. update_project_status(role, clientId, projectId, newStatus)", color=GREEN)
    self_arrow(2, 11.6, "22. _validate_project_status_transition()", color=GREEN)
    arrow(2, 4, 11.45, "23. update_project_status()", color=GREEN)

    # UPDATE
    frame(8.4, 11.0, "alt  [Update]")
    arrow(0, 1, 10.5, "24. insertUpdatedClientDetails()")
    arrow(1, 2, 9.95, "25. update_client(role, clientId, name, phone, email)")
    self_arrow(2, 9.5, "26. _validate + _check_duplicate(excluded=clientId)")
    arrow(2, 4, 9.35, "27. update_client(client)")
    self_arrow(1, 8.9, "28. displayUpdateConfirmation()")

    # DELETE / ARCHIVE
    frame(2.4, 8.2, "alt  [Delete or Archive]")
    arrow(0, 1, 7.6, "29. requestDeleteClient(clientId)")
    arrow(1, 2, 7.05, "30. delete_client(role, clientId)")
    self_arrow(2, 6.6, "31. _check_client_projects(clientId)")
    arrow(2, 4, 6.45, "32. count_projects_for_client(clientId)")
    ret(4, 2, 6.05, "projectsCount")

    frame(3.0, 6.0, "alt  [linked projects > 0]  ->  archive   (Part C: was 'can'tDeleteClient')", color=GREEN)
    arrow(2, 3, 5.4, "33. Client.archive()", color=GREEN)
    arrow(2, 4, 4.85, "34. archive_client(clientId)", color=GREEN)
    ret(2, 1, 4.45, "clientArchived", )
    self_arrow(1, 4.05, "35. displayDeleteConfirmation()  [archived]", color=GREEN)
    ax.text(0.6, 3.5, "else  [linked projects = 0]  ->  delete", fontsize=8.4, weight="bold")
    arrow(2, 4, 3.15, "36. delete_client(clientId)")
    self_arrow(1, 2.75, "37. displayDeleteConfirmation()  [deleted]")

    ax.text(0.5, 1.6,
            "Legend: dashed = returned data.  GREEN = Part C additions / changes vs the Part B diagram.\n"
            "Part B branch 'can'tDeleteClient / displayDeleteError' is replaced by archive-when-linked-projects-exist.",
            fontsize=8, color="#444444")
    return fig


def main():
    state_fig = build_state_diagram()
    seq_fig = build_sequence_diagram()

    state_png = OUT / "Requirement1_StateDiagram_Updated.png"
    state_pdf = OUT / "Requirement1_StateDiagram_Updated.pdf"
    seq_png = OUT / "Requirement1_SequenceDiagram_Updated.png"
    seq_pdf = OUT / "Requirement1_SequenceDiagram_Updated.pdf"

    state_fig.savefig(state_png, dpi=170, bbox_inches="tight")
    state_fig.savefig(state_pdf, bbox_inches="tight")
    seq_fig.savefig(seq_png, dpi=170, bbox_inches="tight")
    seq_fig.savefig(seq_pdf, bbox_inches="tight")

    with PdfPages(OUT / "Requirement1_UpdatedDiagrams_All.pdf") as pdf:
        pdf.savefig(state_fig, bbox_inches="tight")
        pdf.savefig(seq_fig, bbox_inches="tight")

    plt.close(state_fig)
    plt.close(seq_fig)
    print("Requirement 1 updated diagrams written to", OUT)


if __name__ == "__main__":
    main()
