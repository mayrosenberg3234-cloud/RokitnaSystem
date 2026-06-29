"""Shared SQL query-log widget.

Any view can call ``render_sql_query_log()`` to display the live query log
with a search bar and Hebrew action descriptions.
"""

from __future__ import annotations

import re

import streamlit as st

from database import clear_query_log, get_query_log

_TABLE_MAP: dict[str, str] = {
    "CLIENTS": "לקוחות",
    "USERS": "משתמשים",
    "PROJECTS": "פרויקטים",
    "CHANGES": "שינויים",
    "CHANGEHISTORY": "היסטוריית שינויים",
    "DECISIONLOG": "יומן החלטות",
    "FIELDNOTES": "הערות שטח",
    "DRAWINGS": "סרטוטים",
    "INQUIRIES": "פניות",
    "MEETINGS": "פגישות",
    "MILESTONES": "אבני דרך",
    "PAYMENTREQUESTS": "בקשות תשלום",
    "PAYMENTS": "תשלומים",
    "ALERTS": "התראות",
    "REMINDERS": "תזכורות",
    "REPORTS": "דוחות",
    "ACTIVITYLOG": "יומן פעילות",
}

_COL_MAP: dict[str, str] = {
    "clientid": "לקוח",
    "projectid": "פרויקט",
    "userid": "משתמש",
    "changeid": "שינוי",
    "decisionid": "החלטה",
    "noteid": "הערה",
    "drawingid": "סרטוט",
    "meetingid": "פגישה",
    "requestid": "בקשה",
    "reminderid": "תזכורת",
    "reportid": "דוח",
    "alertid": "התראה",
    "username": "שם משתמש",
    "role": "תפקיד",
    "status": "סטטוס",
    "targetrole": "תפקיד יעד",
    "createdbyyuserid": "יוצר",
}


def describe_sql(sql: str) -> str:
    """Return a short Hebrew description for a SQL statement."""
    s = (sql or "").strip()
    upper = s.upper()

    table_match = re.search(r'(?:FROM|INTO|UPDATE)\s+(\w+)', s, re.IGNORECASE)
    if table_match:
        raw = table_match.group(1).upper()
        table_he = _TABLE_MAP.get(raw, table_match.group(1))
    else:
        table_he = "—"

    where_match = re.search(r'WHERE\s+(\w+)\s*[=<>!]', s, re.IGNORECASE)
    where_str = ""
    if where_match:
        col_he = _COL_MAP.get(where_match.group(1).lower(), where_match.group(1))
        where_str = f" לפי {col_he}"

    if upper.startswith("SELECT"):
        if "COUNT" in upper:
            return f"ספירת {table_he}{where_str}"
        if where_str:
            return f"שליפת {table_he}{where_str}"
        return f"שליפת כל ה{table_he}"
    if upper.startswith("INSERT INTO"):
        return f"הוספת רשומה ל{table_he}"
    if upper.startswith("UPDATE"):
        return f"עדכון {table_he}{where_str}"
    if upper.startswith("DELETE"):
        return f"מחיקה מ{table_he}{where_str}"

    return s[:80]


def render_sql_query_log(clear_key: str = "sql_clear_btn") -> None:
    """Render the SQL query log widget with search and Hebrew descriptions."""
    st.markdown("#### יומן שאילתות SQL")

    col1, col2 = st.columns([4, 1])
    with col1:
        search = st.text_input(
            "חיפוש בשאילתות",
            placeholder="חפש לפי טבלה, פעולה, או תיאור...",
            label_visibility="collapsed",
            key=f"sql_search_{clear_key}",
        )
    with col2:
        if st.button("נקה רשימה", use_container_width=True, type="secondary", key=clear_key):
            clear_query_log()
            st.rerun()

    queries = get_query_log(limit=200) or []
    if not queries:
        st.caption("לא נמצאו שאילתות SQL עדיין.")
        return

    rows = []
    for query in queries:
        sql_text = query.sql or "—"
        description = describe_sql(sql_text)
        time_val = query.executed_at or "—"

        if search:
            needle = search.lower()
            if (needle not in sql_text.lower()
                    and needle not in description.lower()
                    and needle not in time_val.lower()):
                continue

        rows.append({"זמן": time_val, "תיאור": description, "שאילתה": sql_text})

    if not rows:
        st.caption("לא נמצאו תוצאות לחיפוש.")
        return

    st.caption(f"מציג {len(rows)} שאילתות")
    st.dataframe(rows, use_container_width=True, hide_index=True)
