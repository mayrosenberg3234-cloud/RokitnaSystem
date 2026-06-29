"""Customer management GUI — Requirement 1.

``CustomerManagementForm`` is the User Class of the digital-client-file
workflow.  It contains presentation and input handling only: validation,
permission checks, lifecycle decisions and database access are delegated to
:class:`controllers.customer_controller.CustomerController`.
"""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from controllers.customer_controller import CustomerController
from controllers.manager_controller import ManagerController
from models.client import Client, ClientStatus
from models.project import Project
from models.user import User

PENDING_DELETE_CLIENT_ID = "pending_delete_client_id"
CUSTOMER_FEEDBACK_KEY = "customer_management_feedback"
NEW_CLIENT_CREDENTIALS = "new_client_credentials"


class CustomerManagementForm:
    """Render the Requirement 1 user interface for an authorised manager."""

    def __init__(
        self,
        controller: CustomerController | None = None,
        manager_controller: ManagerController | None = None,
    ) -> None:
        self._controller = controller or CustomerController()
        self._manager = manager_controller or ManagerController()

    def _set_feedback(self, message: str, feedback_type: str = "success") -> None:
        """Persist a friendly message across Streamlit's mandatory rerun."""
        st.session_state[CUSTOMER_FEEDBACK_KEY] = {
            "message": message,
            "type": feedback_type,
        }

    def _display_pending_feedback(self) -> None:
        """Display one stored message after a successful navigation rerun."""
        feedback = st.session_state.pop(CUSTOMER_FEEDBACK_KEY, None)
        if feedback is None:
            return

        if feedback["type"] == "success":
            st.success(feedback["message"])
        elif feedback["type"] == "warning":
            st.warning(feedback["message"])
        else:
            st.info(feedback["message"])

    # ------------------------------------------------------------------ #
    # Create
    # ------------------------------------------------------------------ #
    def _display_create_form(self, user: User) -> None:
        """Collect and submit details for a new client."""
        st.markdown("#### יצירת לקוח חדש")

        with st.form("create_client_form", clear_on_submit=True):
            name = st.text_input("שם מלא", placeholder="לדוגמה: משפחת לוי")
            phone = st.text_input("טלפון", placeholder="050-1234567")
            email = st.text_input("אימייל", placeholder="name@example.com")
            submitted = st.form_submit_button(
                "צור לקוח",
                use_container_width=True,
            )

        if not submitted:
            return

        # SD-R1: CustomerManagementForm -> CustomerController.create_client()
        result = self._controller.create_client(user.role, name, phone, email)
        if result.success:
            # Keep the one-time credentials so they can be shown (and exported)
            # to the manager after the mandatory rerun.
            st.session_state[NEW_CLIENT_CREDENTIALS] = result.data
            self._set_feedback(result.message, "success")
            st.rerun()

        st.error(result.message)

    def _display_new_credentials(self) -> None:
        """Show (once) the login credentials generated for a new client."""
        creds = st.session_state.get(NEW_CLIENT_CREDENTIALS)
        if not creds:
            return

        with st.container(border=True):
            st.markdown("##### 🔐 פרטי כניסה ללקוח החדש")
            st.caption(
                "מסרו ללקוח את פרטי הכניסה. הסיסמה מוצגת פעם אחת בלבד "
                "ונשמרת במערכת כ-hash בלבד."
            )
            st.code(
                f"שם משתמש: {creds['username']}\nסיסמה: {creds['password']}",
                language=None,
            )
            export_text = (
                "Rokitna — פרטי כניסה ללקוח\n"
                f"שם משתמש: {creds['username']}\n"
                f"סיסמה: {creds['password']}\n"
            )
            cols = st.columns(2)
            cols[0].download_button(
                "⬇️ ייצוא פרטי הכניסה",
                data=export_text.encode("utf-8"),
                file_name=f"client_{creds['client_id']}_credentials.txt",
                mime="text/plain",
                use_container_width=True,
            )
            if cols[1].button("סגור", use_container_width=True, key="close_creds"):
                st.session_state.pop(NEW_CLIENT_CREDENTIALS, None)
                st.rerun()

    # ------------------------------------------------------------------ #
    # Read / client file
    # ------------------------------------------------------------------ #
    def _display_clients_table(self, user: User) -> None:
        """Display all clients, including timestamps required for the live demo."""
        st.markdown("#### רשימת לקוחות")

        result = self._controller.list_clients(user.role)
        if not result.success:
            st.error(result.message)
            return

        clients: list[Client] = result.data
        if not clients:
            st.info("אין לקוחות במערכת עדיין.")
            return

        table = [
            {
                "מזהה": client.client_id,
                "שם": client.name,
                "טלפון": client.phone,
                "אימייל": client.email,
                "סטטוס": client.status.hebrew_label,
                "נוצר בתאריך": client.created_at or "—",
                "עודכן בתאריך": client.updated_at or "—",
            }
            for client in clients
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

        self._display_edit_section(user, clients)

    def _display_client_details(self, user: User, client: Client) -> None:
        """Display the selected client's digital file and linked projects."""
        st.markdown("#### תיק לקוח דיגיטלי")

        details_col, status_col, time_col = st.columns(3)
        details_col.markdown(f"**לקוח:** {client.name}")
        details_col.caption(f"טלפון: {client.phone}")
        details_col.caption(f"אימייל: {client.email}")

        status_col.metric("סטטוס לקוח", client.status.hebrew_label)
        time_col.caption(f"נוצר: {client.created_at or '—'}")
        time_col.caption(f"עודכן: {client.updated_at or '—'}")

        st.markdown("##### פרויקטים מקושרים ללקוח")

        # SD-R1: CustomerController -> DBRepository.list_projects_by_client()
        result = self._controller.list_client_projects(
            user.role,
            client.client_id,
        )
        if not result.success:
            st.error(result.message)
            return

        projects: list[Project] = result.data
        if not projects:
            st.info("ללקוח זה עדיין אין פרויקטים מקושרים.")
        else:
            project_table = [
                {
                    "מזהה פרויקט": project.project_id,
                    "שם פרויקט": project.project_name,
                    "סטטוס": project.status.hebrew_label,
                    "נוצר בתאריך": project.created_at or "—",
                    "עודכן בתאריך": project.updated_at or "—",
                }
                for project in projects
            ]
            st.dataframe(project_table, use_container_width=True, hide_index=True)

        self._display_link_project_form(user, client)
        self._display_project_status_update_form(user, client, projects)
        self._display_schedule_meeting_form(user, client, projects)
        self._display_client_reminder_form(user, client)
        self._display_client_inquiries(user, client)

    def _display_link_project_form(self, user: User, client: Client) -> None:
        """Allow an office manager to create and link an active project.

        A newly opened project always begins in the ``Active`` state.  Later
        progress is reflected only through the explicit project-status-update
        flow, which preserves the Project State Diagram lifecycle.
        """
        st.markdown("##### קישור פרויקט חדש ללקוח")

        if client.status == ClientStatus.ARCHIVED:
            st.info("לא ניתן לקשר פרויקט חדש ללקוח בארכיון.")
            return

        st.caption(
            "פרויקט חדש נוצר בסטטוס 'פעיל' ונשמר עם מזהה הלקוח הנבחר, "
            "ולכן יוצג מיד בתיק הלקוח הדיגיטלי."
        )

        with st.form(f"link_project_form_{client.client_id}", clear_on_submit=True):
            project_name = st.text_input(
                "שם הפרויקט",
                placeholder="לדוגמה: שיפוץ דירת משפחת לוי",
            )
            submitted = st.form_submit_button(
                "קשר פרויקט ללקוח",
                use_container_width=True,
            )

        if not submitted:
            return

        # SD-R1: CustomerManagementForm -> CustomerController.link_project_to_client()
        link_result = self._controller.link_project_to_client(
            user.role,
            client.client_id,
            project_name,
        )
        if link_result.success:
            self._set_feedback(
                f"{link_result.message} מזהה הפרויקט החדש: {link_result.data}",
                "success",
            )
            st.rerun()

        st.error(link_result.message)

    def _display_project_status_update_form(
        self,
        user: User,
        client: Client,
        projects: list[Project],
    ) -> None:
        """Update a linked project's lifecycle status according to progress.

        The selection is scoped to projects already linked to the currently
        selected client.  Only next statuses permitted by ``Project``'s state
        machine are presented to the manager.
        """
        st.markdown("##### עדכון סטטוס פרויקט לפי התקדמות")

        if client.status == ClientStatus.ARCHIVED:
            st.info("לא ניתן לעדכן סטטוסי פרויקטים עבור לקוח בארכיון.")
            return

        if not projects:
            st.info("יש לקשר פרויקט ללקוח לפני עדכון סטטוס ההתקדמות.")
            return

        updatable_projects = [
            project for project in projects if project.available_next_statuses()
        ]
        if not updatable_projects:
            st.info("כל הפרויקטים המקושרים ללקוח הושלמו ואין להם מעבר סטטוס נוסף.")
            return

        project_options = {
            (
                f"{project.project_id} — {project.project_name} "
                f"(סטטוס נוכחי: {project.status.hebrew_label})"
            ): project
            for project in updatable_projects
        }
        selected_project_label = st.selectbox(
            "בחר פרויקט לעדכון סטטוס",
            list(project_options.keys()),
            key=f"project_status_select_{client.client_id}",
        )
        selected_project = project_options[selected_project_label]
        allowed_statuses = selected_project.available_next_statuses()

        st.caption(
            "מעברים אפשריים לפי מחזור חיי הפרויקט: "
            "פעיל ←→ בהמתנה, ופעיל/בהמתנה → הושלם. "
            "פרויקט שהושלם הוא מצב סופי."
        )

        with st.form(
            f"update_project_status_form_{client.client_id}_{selected_project.project_id}"
        ):
            new_status = st.selectbox(
                "סטטוס חדש",
                options=list(allowed_statuses),
                format_func=lambda status: status.hebrew_label,
            )
            submitted = st.form_submit_button(
                "עדכן סטטוס פרויקט",
                use_container_width=True,
            )

        if not submitted:
            return

        # SD-R1: CustomerManagementForm -> CustomerController.update_project_status()
        update_result = self._controller.update_project_status(
            user.role,
            client.client_id,
            selected_project.project_id,
            new_status,
        )
        if update_result.success:
            self._set_feedback(update_result.message, "success")
            st.rerun()

        st.error(update_result.message)

    def _display_schedule_meeting_form(
        self,
        user: User,
        client: Client,
        projects: list[Project],
    ) -> None:
        """Let the office manager schedule a meeting for one of the projects."""
        st.markdown("##### קביעת פגישה ללקוח")

        if client.status == ClientStatus.ARCHIVED:
            st.info("לא ניתן לקבוע פגישות ללקוח בארכיון.")
            return
        if not projects:
            st.info("יש לקשר פרויקט ללקוח לפני קביעת פגישה.")
            return

        project_options = {
            f"{p.project_id} — {p.project_name}": p for p in projects
        }
        with st.form(f"schedule_meeting_form_{client.client_id}", clear_on_submit=True):
            selected_label = st.selectbox(
                "פרויקט", list(project_options.keys())
            )
            date_col, time_col = st.columns(2)
            meeting_date = date_col.date_input("תאריך הפגישה")
            meeting_time = time_col.time_input("שעת הפגישה")
            location = st.text_input("מיקום", placeholder="לדוגמה: משרד רוקיטנה")
            summary = st.text_input("נושא הפגישה", placeholder="לדוגמה: בחירת ריצוף")
            submitted = st.form_submit_button(
                "קבע פגישה", use_container_width=True
            )

        if not submitted:
            return

        selected_project = project_options[selected_label]
        result = self._controller.schedule_meeting(
            user.role,
            client.client_id,
            selected_project.project_id,
            meeting_date.isoformat(),
            meeting_time.strftime("%H:%M"),
            location,
            summary,
        )
        if result.success:
            self._set_feedback(result.message, "success")
            st.rerun()
        st.error(result.message)

    def _display_client_reminder_form(self, user: User, client: Client) -> None:
        """Let the office manager send a reminder to this client."""
        st.markdown("##### שליחת תזכורת ללקוח")
        with st.form(f"client_reminder_form_{client.client_id}", clear_on_submit=True):
            message = st.text_input(
                "תוכן התזכורת",
                placeholder="לדוגמה: נא לאשר את בחירת חומרי הגמר עד סוף השבוע.",
            )
            submitted = st.form_submit_button(
                "שלח תזכורת ללקוח", use_container_width=True
            )
        if not submitted:
            return
        result = self._manager.send_reminder_to_client(
            user, client.client_id, message
        )
        if result.success:
            self._set_feedback(result.message, "success")
            st.rerun()
        st.error(result.message)

    def _display_client_inquiries(self, user: User, client: Client) -> None:
        """Show the inquiries this client has submitted to the office."""
        st.markdown("##### פניות שהתקבלו מהלקוח")
        result = self._controller.list_client_inquiries(
            user.role, client.client_id
        )
        if not result.success:
            st.caption(result.message)
            return

        inquiries = result.data
        if not inquiries:
            st.caption("לא התקבלו פניות מלקוח זה.")
            return

        table = [
            {
                "מזהה": inquiry.inquiry_id,
                "תוכן": inquiry.content,
                "סטטוס": inquiry.status.hebrew_label,
                "נשלחה בתאריך": inquiry.created_at or "—",
            }
            for inquiry in inquiries
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------ #
    # Update / delete client
    # ------------------------------------------------------------------ #
    def _display_edit_section(
        self,
        user: User,
        clients: Iterable[Client],
    ) -> None:
        """Select one client, display its file, then update or request deletion."""
        st.markdown("#### עדכון / מחיקת לקוח")

        options = {f"{client.client_id} — {client.name}": client for client in clients}
        selected_label = st.selectbox("בחר לקוח", list(options.keys()))
        selected_client = options[selected_label]

        # Use the controller's explicit get_client() action so the selected
        # record is refreshed before it is presented as the digital client file.
        details_result = self._controller.get_client(
            user.role,
            selected_client.client_id,
        )
        if not details_result.success:
            st.error(details_result.message)
            return

        client: Client = details_result.data
        self._display_client_details(user, client)

        if client.status == ClientStatus.ARCHIVED:
            st.info(
                "לקוח זה נמצא בארכיון ונשמר לצורכי היסטוריית פרויקטים. "
                "ניתן לצפות בפרטיו בלבד."
            )
            return

        st.caption(
            "סטטוס הלקוח מנוהל לפי מחזור החיים העסקי: לקוח בעל פרויקטים "
            "מקושרים מועבר לארכיון בעת בקשת מחיקה, כדי לשמור על היסטוריית הפרויקטים."
        )

        with st.form("edit_client_form"):
            name = st.text_input("שם מלא", value=client.name)
            phone = st.text_input("טלפון", value=client.phone)
            email = st.text_input("אימייל", value=client.email)

            update_col, delete_col = st.columns(2)
            update_clicked = update_col.form_submit_button(
                "עדכן פרטי לקוח",
                use_container_width=True,
            )
            request_delete_clicked = delete_col.form_submit_button(
                "בקשת מחיקה",
                use_container_width=True,
            )

        if update_clicked:
            # The client lifecycle status is intentionally not editable here.
            result = self._controller.update_client(
                user.role,
                client.client_id,
                name,
                phone,
                email,
            )
            if result.success:
                self._set_feedback(result.message, "success")
                st.rerun()
            st.error(result.message)

        if request_delete_clicked:
            st.session_state[PENDING_DELETE_CLIENT_ID] = client.client_id
            st.rerun()

        if st.session_state.get(PENDING_DELETE_CLIENT_ID) == client.client_id:
            self._display_delete_confirmation(user, client)

    def _display_delete_confirmation(self, user: User, client: Client) -> None:
        """Ask for explicit confirmation before requesting deletion/archiving."""
        st.warning(
            f"האם את בטוחה שברצונך למחוק את הלקוח '{client.name}'? "
            "אם קיימים פרויקטים מקושרים, הלקוח יועבר לארכיון במקום להימחק."
        )
        confirm_col, cancel_col = st.columns(2)

        if confirm_col.button(
            "אישור מחיקה",
            key=f"confirm_delete_{client.client_id}",
            use_container_width=True,
        ):
            # SD-R1: CustomerManagementForm -> CustomerController.delete_client()
            result = self._controller.delete_client(
                user.role,
                client.client_id,
            )
            st.session_state.pop(PENDING_DELETE_CLIENT_ID, None)

            if result.success:
                self._set_feedback(result.message, "success")
                st.rerun()

            st.error(result.message)

        if cancel_col.button(
            "ביטול",
            key=f"cancel_delete_{client.client_id}",
            use_container_width=True,
        ):
            st.session_state.pop(PENDING_DELETE_CLIENT_ID, None)
            self._set_feedback("בקשת המחיקה בוטלה.", "info")
            st.rerun()

    # ------------------------------------------------------------------ #
    # Public screen entry point
    # ------------------------------------------------------------------ #
    def render(self, user: User) -> None:
        """Render the complete Requirement 1 screen."""
        st.header("ניהול תיק לקוח דיגיטלי")
        st.caption(
            "יצירה, צפייה, עדכון ומחיקה מבוקרת של לקוחות, "
            "כולל קישור פרויקטים, עדכון סטטוס התקדמות וחותמות זמן."
        )
        self._display_pending_feedback()
        self._display_new_credentials()
        st.divider()
        self._display_create_form(user)
        st.divider()
        self._display_clients_table(user)


# Compatibility wrapper: app.py continues to call customer_management.render(user).
_customer_management_form = CustomerManagementForm()


def render(user: User) -> None:
    """Render the customer-management page via the User Class instance."""
    _customer_management_form.render(user)
