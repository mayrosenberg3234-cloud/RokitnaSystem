"""Client portal view.

The landing experience for a logged-in client:
* reminders the office sent them;
* their own projects and progress status;
* their meetings (confirming the ones that need their approval);
* the project drawings (view / download);
* documented project changes to approve or reject;
* a box to submit an inquiry to a chosen office role, with their inquiry history.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from controllers.client_controller import ClientController, INQUIRY_TARGETS
from models.change import ChangeStatus
from models.meeting import MeetingStatus
from models.user import User
from utils.sql_log_widget import render_sql_query_log

INQUIRY_FEEDBACK_KEY = "client_inquiry_feedback"


class ClientPortal:
    """Render the client portal: read-only views plus the client's actions."""

    def __init__(self, controller: ClientController | None = None) -> None:
        self._controller = controller or ClientController()

    def _set_feedback(self, message: str) -> None:
        st.session_state[INQUIRY_FEEDBACK_KEY] = message

    def _display_pending_feedback(self) -> None:
        feedback = st.session_state.pop(INQUIRY_FEEDBACK_KEY, None)
        if feedback:
            st.success(feedback)

    # ------------------------------------------------------------------ #
    # Reminders
    # ------------------------------------------------------------------ #
    def _display_reminders(self, user: User) -> None:
        result = self._controller.view_my_reminders(user)
        if not result.success or not result.data:
            return
        st.markdown("#### תזכורות מהמשרד")
        for reminder in result.data:
            st.info(f"{reminder.message}  \n*{reminder.created_at or ''}*")

    # ------------------------------------------------------------------ #
    # Projects
    # ------------------------------------------------------------------ #
    def _display_my_projects(self, user: User) -> None:
        st.markdown("#### הפרויקטים שלי וסטטוס ההתקדמות")
        result = self._controller.view_my_projects(user)
        if not result.success:
            st.info(result.message)
            return
        projects = result.data
        if not projects:
            st.caption("עדיין אין פרויקטים המשויכים אליך.")
            return
        table = [
            {
                "מזהה פרויקט": p.project_id,
                "שם פרויקט": p.project_name,
                "סטטוס התקדמות": p.status.hebrew_label,
                "נפתח בתאריך": p.created_at or "—",
                "עודכן בתאריך": p.updated_at or "—",
            }
            for p in projects
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------ #
    # Meetings (confirm the proposed ones)
    # ------------------------------------------------------------------ #
    def _display_my_meetings(self, user: User) -> None:
        st.markdown("#### הפגישות הקרובות שלי")
        result = self._controller.view_my_meetings(user)
        if not result.success:
            st.info(result.message)
            return
        meetings = result.data
        if not meetings:
            st.caption("אין פגישות עתידיות שנקבעו עבורך כרגע.")
            return
        for m in meetings:
            cols = st.columns([3, 2, 3, 2])
            cols[0].markdown(f"**{m.meeting_date}** {m.meeting_time}")
            cols[1].caption(m.location)
            cols[2].caption(m.summary)
            if m.status == MeetingStatus.PROPOSED:
                if cols[3].button(
                    "אשר פגישה", key=f"confirm_meet_{m.meeting_id}", type="primary"
                ):
                    res = self._controller.confirm_meeting(user, m.meeting_id)
                    if res.success:
                        self._set_feedback(res.message)
                        st.rerun()
                    st.error(res.message)
            else:
                cols[3].success(m.status.hebrew_label)

    # ------------------------------------------------------------------ #
    # Drawings
    # ------------------------------------------------------------------ #
    def _display_my_drawings(self, user: User) -> None:
        st.markdown("#### סרטוטים")
        result = self._controller.view_my_drawings(user)
        if not result.success:
            st.info(result.message)
            return
        drawings = result.data
        if not drawings:
            st.caption("עדיין לא הועלו סרטוטים לפרויקטים שלך.")
            return
        for d in drawings:
            cols = st.columns([4, 3, 3])
            cols[0].markdown(f"**{d.file_name}**")
            cols[1].caption(d.description or "—")
            path = Path(d.stored_path)
            if path.exists():
                cols[2].download_button(
                    "⬇️ הורד",
                    data=path.read_bytes(),
                    file_name=d.file_name,
                    key=f"dl_drawing_{d.drawing_id}",
                    use_container_width=True,
                )
            else:
                cols[2].caption("הקובץ אינו זמין")

    # ------------------------------------------------------------------ #
    # Changes to approve
    # ------------------------------------------------------------------ #
    def _display_changes(self, user: User) -> None:
        st.markdown("#### שינויים לאישור")
        result = self._controller.view_my_changes(user)
        if not result.success:
            st.info(result.message)
            return
        changes = result.data
        if not changes:
            st.caption("אין שינויים בפרויקטים שלך.")
            return

        pending = [c for c in changes if c.status == ChangeStatus.PENDING]
        decided = [c for c in changes if c.status != ChangeStatus.PENDING]

        for c in pending:
            with st.container(border=True):
                st.markdown(f"**{c.description}**")
                st.caption(f"עלות השינוי: {c.cost:,.2f} ₪ · נשלח: {c.created_at or '—'}")
                approve_col, reject_col = st.columns(2)
                if approve_col.button(
                    "אשר שינוי", key=f"approve_change_{c.change_id}",
                    use_container_width=True, type="primary",
                ):
                    res = self._controller.decide_change(user, c.change_id, True)
                    if res.success:
                        self._set_feedback(res.message)
                        st.rerun()
                    st.error(res.message)
                if reject_col.button(
                    "דחה שינוי", key=f"reject_change_{c.change_id}",
                    use_container_width=True,
                ):
                    res = self._controller.decide_change(user, c.change_id, False)
                    if res.success:
                        self._set_feedback(res.message)
                        st.rerun()
                    st.error(res.message)

        if decided:
            st.caption("שינויים שכבר טופלו:")
            st.dataframe(
                [
                    {
                        "תיאור": c.description,
                        "עלות": f"{c.cost:,.2f}",
                        "סטטוס": c.status.hebrew_label,
                        "הוחלט בתאריך": c.decided_at or "—",
                    }
                    for c in decided
                ],
                use_container_width=True,
                hide_index=True,
            )

    # ------------------------------------------------------------------ #
    # Inquiries
    # ------------------------------------------------------------------ #
    def _display_inquiry_form(self, user: User) -> None:
        st.markdown("#### שליחת פנייה / בקשה")
        target_labels = {role.hebrew_label: role.value for role in INQUIRY_TARGETS}
        with st.form("client_inquiry_form", clear_on_submit=True):
            target_label = st.selectbox("נמען הפנייה", list(target_labels.keys()))
            content = st.text_area(
                "תוכן הפנייה",
                height=120,
                placeholder="לדוגמה: אשמח לתאם פגישה נוספת לבחירת ריצוף.",
            )
            submitted = st.form_submit_button("שלח פנייה", use_container_width=True)

        if not submitted:
            return
        result = self._controller.submit_inquiry(
            user, content, target_labels[target_label]
        )
        if result.success:
            self._set_feedback(result.message)
            st.rerun()
        st.error(result.message)

    def _display_my_inquiries(self, user: User) -> None:
        st.markdown("##### הפניות שלי")
        result = self._controller.list_my_inquiries(user)
        if not result.success:
            st.caption(result.message)
            return
        inquiries = result.data
        if not inquiries:
            st.caption("עדיין לא שלחת פניות.")
            return
        target_label = {role.value: role.hebrew_label for role in INQUIRY_TARGETS}
        st.dataframe(
            [
                {
                    "מזהה": i.inquiry_id,
                    "נמען": target_label.get(i.target_role, i.target_role),
                    "תוכן": i.content,
                    "סטטוס": i.status.hebrew_label,
                    "נשלחה בתאריך": i.created_at or "—",
                }
                for i in inquiries
            ],
            use_container_width=True,
            hide_index=True,
        )

    def render(self, user: User) -> None:
        """Render the full client portal."""
        st.markdown("#### הפורטל שלי")
        st.caption(
            "כאן ניתן לעקוב אחר הפרויקטים שלך, לראות פגישות וסרטוטים, "
            "לאשר שינויים ולשלוח פניות למשרד."
        )
        self._display_pending_feedback()
        self._display_reminders(user)
        st.divider()
        self._display_my_projects(user)
        st.divider()
        self._display_my_meetings(user)
        st.divider()
        self._display_my_drawings(user)
        st.divider()
        self._display_changes(user)
        st.divider()
        self._display_inquiry_form(user)
        self._display_my_inquiries(user)
        st.divider()
        render_sql_query_log(clear_key="sql_clear_client")


_client_portal = ClientPortal()


def render(user: User) -> None:
    """Render the client portal via the shared instance."""
    _client_portal.render(user)
