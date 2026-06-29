"""Login view.

Renders the login form and, on success, stores the authenticated user in the
Streamlit session state so the rest of the application can react to it.
"""

from __future__ import annotations

import streamlit as st

from config import APP_SUBTITLE, APP_TITLE
from controllers.auth_controller import AuthController

_auth_controller = AuthController()


def render() -> None:
    """Render the centered, branded login screen."""
    st.markdown("<div style='height:5vh'></div>", unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1.5, 1])

    with center:
        st.markdown(
            f"""
            <div style="text-align:center;margin-bottom:1.3rem;direction:rtl;">
              <div style="width:68px;height:68px;border-radius:20px;background:var(--accent);
                          color:#fff;display:flex;align-items:center;justify-content:center;
                          font-family:var(--display);font-size:2.1rem;margin:0 auto .9rem;
                          box-shadow:0 10px 28px rgba(161,98,7,.28);">R</div>
              <div style="font-family:var(--display);font-size:2.2rem;color:var(--ink);line-height:1.1;">{APP_TITLE}</div>
              <div style="color:var(--muted);font-size:.95rem;margin-top:.35rem;">{APP_SUBTITLE}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            st.markdown("##### כניסה למערכת")
            username = st.text_input("שם משתמש", placeholder="לדוגמה: manager")
            password = st.text_input("סיסמה", type="password")
            submitted = st.form_submit_button("התחברות", use_container_width=True)

        if submitted:
            result = _auth_controller.login(username, password)
            if result.success:
                st.session_state["user"] = result.data
                st.session_state["page"] = "dashboard"
                st.rerun()
            else:
                st.error(result.message)

        with st.expander("משתמשי הדגמה"):
            st.markdown(
                "- **manager** / 1234 — מנהל משרד\n"
                "- **architect** / 1234 — אדריכלית\n"
                "- **client** / 1234 — לקוח"
            )
