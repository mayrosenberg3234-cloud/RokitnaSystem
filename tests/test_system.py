"""End-to-end unit tests for the Rokitna system.

Each test runs against a fresh, isolated SQLite database created in a temporary
directory so the real ``rokitna.db`` is never touched.  The tests exercise the
controllers (which in turn drive validation, permissions and the repository).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import database
import init_db
from controllers import report_controller as report_module
from controllers.architect_controller import ArchitectController
from controllers.auth_controller import AuthController
from controllers.client_controller import ClientController
from controllers.customer_controller import CustomerController
from controllers.decision_controller import DecisionController
from controllers.manager_controller import ManagerController
from controllers.report_controller import ReportController
from models.change_history import ChangeHistory
from models.client import Client, ClientStatus
from models.decision_entry_session import DecisionEntrySession, DecisionEntryStatus
from models.decision_log import DecisionLog
from models.payment import Payment
from models.payment_request import PaymentRequest
from models.project import Project, ProjectStatus
from models.report import Report, ReportStatus, ReportType
from models.user import RoleEnum, User
from repositories.db_repository import DBRepository


class RokitnaTestCase(unittest.TestCase):
    """Base test case that provisions an isolated database per test."""

    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = Path(self._tmp_dir.name)

        # Redirect every database connection to the temporary file.
        self._original_db_path = database.DB_PATH
        database.DB_PATH = tmp_path / "test.db"

        # Redirect CSV exports into the temporary directory too.
        self._original_exports = report_module.EXPORTS_DIR
        report_module.EXPORTS_DIR = tmp_path / "exports"

        init_db.create_tables()
        init_db.seed_users()

        self.repo = DBRepository()
        self.auth = AuthController(self.repo)
        self.customers = CustomerController(self.repo)
        self.decisions = DecisionController(self.repo)
        self.reports = ReportController(self.repo)

    def tearDown(self) -> None:
        database.DB_PATH = self._original_db_path
        report_module.EXPORTS_DIR = self._original_exports
        self._tmp_dir.cleanup()

    def _create_project(self) -> int:
        client_id = self.repo.create_client(
            Client(name="לקוח בדיקה", phone="050-0000000", email="qa@example.com")
        )
        return self.repo.create_project(
            Project(client_id=client_id, project_name="פרויקט בדיקה")
        )


class TestAuthentication(RokitnaTestCase):
    def test_login_success(self) -> None:
        result = self.auth.login("manager", "1234")
        self.assertTrue(result.success)
        self.assertEqual(result.data.role, RoleEnum.OFFICE_MANAGER)

    def test_login_failure_wrong_password(self) -> None:
        result = self.auth.login("manager", "wrong")
        self.assertFalse(result.success)

    def test_login_failure_empty_fields(self) -> None:
        result = self.auth.login("", "")
        self.assertFalse(result.success)


class TestPermissions(RokitnaTestCase):
    def test_permission_denied_architect_manage_clients(self) -> None:
        result = self.customers.create_client(
            RoleEnum.ARCHITECT, "x", "050-1111111", "x@example.com"
        )
        self.assertFalse(result.success)

    def test_permission_denied_client_generate_report(self) -> None:
        result = self.reports.generate_management_report(
            RoleEnum.CLIENT, "active_projects"
        )
        self.assertFalse(result.success)


class TestCustomers(RokitnaTestCase):
    def test_create_client(self) -> None:
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "דנה", "050-1234567", "dana@example.com"
        )
        self.assertTrue(result.success)
        self.assertEqual(len(self.repo.list_clients()), 1)

    def test_create_client_records_activity_log_with_timestamp(self) -> None:
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "רוני", "050-7777777", "roni@example.com"
        )
        self.assertTrue(result.success)

        connection = database.get_connection()
        try:
            row = connection.execute(
                "SELECT action, createdAt FROM ActivityLog WHERE entityType = ? ORDER BY activityId DESC LIMIT 1",
                ("Client",),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["action"], "create_client")
            self.assertIsNotNone(row["createdAt"])
        finally:
            connection.close()

    def test_list_activity_log_returns_recent_entries(self) -> None:
        self.repo.create_client(
            Client(name="עידו", phone="050-8888888", email="ido@example.com")
        )
        logs = self.repo.list_activity_log(limit=5)
        self.assertGreaterEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "create_client")

    def test_list_activity_log_handles_empty_and_non_positive_limits(self) -> None:
        self.assertEqual(self.repo.list_activity_log(limit=0), [])
        self.assertEqual(self.repo.list_activity_log(limit=-3), [])
        self.assertEqual(self.repo.list_activity_log(limit=1), [])

    def test_create_duplicate_phone(self) -> None:
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "א", "050-1234567", "a@example.com"
        )
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "ב", "050-1234567", "b@example.com"
        )
        self.assertFalse(result.success)

    def test_create_invalid_email(self) -> None:
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "ג", "050-7654321", "not-an-email"
        )
        self.assertFalse(result.success)

    def test_update_client(self) -> None:
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "ישן", "050-2222222", "old@example.com"
        )
        client = self.repo.list_clients()[0]
        result = self.customers.update_client(
            RoleEnum.OFFICE_MANAGER,
            client.client_id,
            "חדש",
            "050-3333333",
            "new@example.com",
        )
        self.assertTrue(result.success)
        self.assertEqual(self.repo.get_client(client.client_id).name, "חדש")

    def test_linked_project_always_starts_active(self) -> None:
        """A project opened through the client file begins in ProjectActive."""
        client_id = self.repo.create_client(
            Client(
                name="לקוח לפרויקט חדש",
                phone="050-2121212",
                email="new-project@example.com",
            )
        )

        result = self.customers.link_project_to_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            "פרויקט חדש",
        )

        self.assertTrue(result.success)
        project = self.repo.get_project(result.data)
        self.assertIsNotNone(project)
        self.assertEqual(project.status, ProjectStatus.ACTIVE)

    def test_delete_client_without_projects(self) -> None:
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "למחיקה", "050-4444444", "del@example.com"
        )
        client = self.repo.list_clients()[0]
        result = self.customers.delete_client(
            RoleEnum.OFFICE_MANAGER, client.client_id
        )
        self.assertTrue(result.success)
        self.assertIsNone(self.repo.get_client(client.client_id))

    def test_delete_client_with_active_project_archives(self) -> None:
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "פעיל", "050-5555555", "act@example.com"
        )
        client = self.repo.list_clients()[0]
        self.repo.create_project(
            Project(client_id=client.client_id, project_name="פרויקט פעיל")
        )
        result = self.customers.delete_client(
            RoleEnum.OFFICE_MANAGER, client.client_id
        )
        self.assertTrue(result.success)
        self.assertEqual(
            self.repo.get_client(client.client_id).status, ClientStatus.ARCHIVED
        )

    def test_delete_client_with_completed_project_archives(self) -> None:
        """A completed project still protects the client history from deletion."""
        client_id = self.repo.create_client(
            Client(
                name="לקוח עם פרויקט שהושלם",
                phone="050-6666666",
                email="completed@example.com",
            )
        )
        self.repo.create_project(
            Project(
                client_id=client_id,
                project_name="פרויקט שהושלם",
                status=ProjectStatus.COMPLETED,
            )
        )

        result = self.customers.delete_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            self.repo.get_client(client_id).status,
            ClientStatus.ARCHIVED,
        )

    def test_delete_client_with_on_hold_project_archives(self) -> None:
        """A paused project is also a linked historical record."""
        client_id = self.repo.create_client(
            Client(
                name="לקוח עם פרויקט מושהה",
                phone="050-7777777",
                email="onhold@example.com",
            )
        )
        self.repo.create_project(
            Project(
                client_id=client_id,
                project_name="פרויקט בהמתנה",
                status=ProjectStatus.ON_HOLD,
            )
        )

        result = self.customers.delete_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            self.repo.get_client(client_id).status,
            ClientStatus.ARCHIVED,
        )

    def test_archived_client_cannot_be_updated(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח בארכיון",
                phone="050-3131313",
                email="archived-update@example.com",
                status=ClientStatus.ARCHIVED,
            )
        )

        result = self.customers.update_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            "שם חדש",
            "050-3131313",
            "archived-update@example.com",
        )

        self.assertFalse(result.success)
        self.assertEqual(self.repo.get_client(client_id).name, "לקוח בארכיון")

    def test_archived_client_cannot_be_deleted_again(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח שכבר בארכיון",
                phone="050-4141414",
                email="already-archived@example.com",
                status=ClientStatus.ARCHIVED,
            )
        )

        result = self.customers.delete_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
        )

        self.assertFalse(result.success)
        self.assertEqual(
            self.repo.get_client(client_id).status,
            ClientStatus.ARCHIVED,
        )

    def test_get_client_returns_selected_client(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח לתצוגה",
                phone="050-8888888",
                email="details@example.com",
            )
        )

        result = self.customers.get_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data.client_id, client_id)
        self.assertEqual(result.data.name, "לקוח לתצוגה")

    def test_list_client_projects_returns_only_selected_client_projects(self) -> None:
        first_client_id = self.repo.create_client(
            Client(
                name="לקוח פרויקטים",
                phone="050-9999999",
                email="projects@example.com",
            )
        )
        second_client_id = self.repo.create_client(
            Client(
                name="לקוח נוסף",
                phone="050-1010101",
                email="other-projects@example.com",
            )
        )
        self.repo.create_project(
            Project(client_id=first_client_id, project_name="פרויקט ראשון")
        )
        self.repo.create_project(
            Project(client_id=second_client_id, project_name="פרויקט של לקוח אחר")
        )

        result = self.customers.list_client_projects(
            RoleEnum.OFFICE_MANAGER,
            first_client_id,
        )

        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].client_id, first_client_id)
        self.assertEqual(result.data[0].project_name, "פרויקט ראשון")

    def test_architect_cannot_list_client_projects(self) -> None:
        result = self.customers.list_client_projects(
            RoleEnum.ARCHITECT,
            1,
        )
        self.assertFalse(result.success)

    def test_office_manager_links_new_project_to_client(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח לקישור פרויקט",
                phone="050-1239876",
                email="link-project@example.com",
            )
        )

        result = self.customers.link_project_to_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            "שיפוץ דירת משפחת לוי",
        )

        self.assertTrue(result.success)
        self.assertIsInstance(result.data, int)

        project = self.repo.get_project(result.data)
        self.assertIsNotNone(project)
        self.assertEqual(project.client_id, client_id)
        self.assertEqual(project.project_name, "שיפוץ דירת משפחת לוי")
        self.assertEqual(project.status, ProjectStatus.ACTIVE)

        linked_projects = self.repo.list_projects_by_client(client_id)
        self.assertEqual(len(linked_projects), 1)
        self.assertEqual(linked_projects[0].project_id, result.data)

    def test_architect_cannot_link_project_to_client(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח הרשאות",
                phone="050-4567890",
                email="permissions-link@example.com",
            )
        )

        result = self.customers.link_project_to_client(
            RoleEnum.ARCHITECT,
            client_id,
            "פרויקט ללא הרשאה",
        )

        self.assertFalse(result.success)
        self.assertEqual(self.repo.list_projects_by_client(client_id), [])

    def test_cannot_link_project_to_archived_client(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח בארכיון",
                phone="050-9876543",
                email="archived-link@example.com",
            )
        )
        self.repo.archive_client(client_id)

        result = self.customers.link_project_to_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            "פרויקט שלא אמור להיווצר",
        )

        self.assertFalse(result.success)
        self.assertEqual(self.repo.list_projects_by_client(client_id), [])

    def test_link_project_requires_name(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח ללא שם פרויקט",
                phone="050-1122334",
                email="no-project-name@example.com",
            )
        )

        result = self.customers.link_project_to_client(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            "   ",
        )

        self.assertFalse(result.success)
        self.assertEqual(self.repo.list_projects_by_client(client_id), [])


    # ------------------------------------------------------------------ #
    # Requirement 1: project status according to progress
    # ------------------------------------------------------------------ #
    def test_office_manager_updates_linked_project_status(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח לעדכון סטטוס",
                phone="050-5551212",
                email="status-update@example.com",
            )
        )
        project_id = self.repo.create_project(
            Project(
                client_id=client_id,
                project_name="שיפוץ משרד קבלה",
                status=ProjectStatus.ACTIVE,
            )
        )

        result = self.customers.update_project_status(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            project_id,
            ProjectStatus.ON_HOLD,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data.status, ProjectStatus.ON_HOLD)
        self.assertIsNotNone(result.data.updated_at)
        self.assertEqual(
            self.repo.get_project(project_id).status,
            ProjectStatus.ON_HOLD,
        )

    def test_office_manager_can_resume_on_hold_project(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח לחידוש פרויקט",
                phone="050-5552323",
                email="resume-project@example.com",
            )
        )
        project_id = self.repo.create_project(
            Project(
                client_id=client_id,
                project_name="תכנון מטבח",
                status=ProjectStatus.ON_HOLD,
            )
        )

        result = self.customers.update_project_status(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            project_id,
            ProjectStatus.ACTIVE,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            self.repo.get_project(project_id).status,
            ProjectStatus.ACTIVE,
        )

    def test_office_manager_completes_active_project(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח להשלמת פרויקט",
                phone="050-5553434",
                email="complete-project@example.com",
            )
        )
        project_id = self.repo.create_project(
            Project(
                client_id=client_id,
                project_name="עיצוב חדרי ילדים",
                status=ProjectStatus.ACTIVE,
            )
        )

        result = self.customers.update_project_status(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            project_id,
            ProjectStatus.COMPLETED,
        )

        self.assertTrue(result.success)
        self.assertEqual(
            self.repo.get_project(project_id).status,
            ProjectStatus.COMPLETED,
        )

    def test_completed_project_cannot_be_reopened(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח עם פרויקט שהושלם",
                phone="050-5554545",
                email="completed-status@example.com",
            )
        )
        project_id = self.repo.create_project(
            Project(
                client_id=client_id,
                project_name="פרויקט שהושלם",
                status=ProjectStatus.COMPLETED,
            )
        )

        result = self.customers.update_project_status(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            project_id,
            ProjectStatus.ACTIVE,
        )

        self.assertFalse(result.success)
        self.assertEqual(
            self.repo.get_project(project_id).status,
            ProjectStatus.COMPLETED,
        )

    def test_project_status_update_rejects_project_of_another_client(self) -> None:
        first_client_id = self.repo.create_client(
            Client(
                name="לקוח ראשון",
                phone="050-5555656",
                email="first-owner@example.com",
            )
        )
        second_client_id = self.repo.create_client(
            Client(
                name="לקוח שני",
                phone="050-5556767",
                email="second-owner@example.com",
            )
        )
        project_id = self.repo.create_project(
            Project(
                client_id=first_client_id,
                project_name="פרויקט של הלקוח הראשון",
            )
        )

        result = self.customers.update_project_status(
            RoleEnum.OFFICE_MANAGER,
            second_client_id,
            project_id,
            ProjectStatus.ON_HOLD,
        )

        self.assertFalse(result.success)
        self.assertEqual(
            self.repo.get_project(project_id).status,
            ProjectStatus.ACTIVE,
        )

    def test_architect_cannot_update_project_status(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח הרשאות סטטוס",
                phone="050-5557878",
                email="status-permission@example.com",
            )
        )
        project_id = self.repo.create_project(
            Project(client_id=client_id, project_name="פרויקט מוגן")
        )

        result = self.customers.update_project_status(
            RoleEnum.ARCHITECT,
            client_id,
            project_id,
            ProjectStatus.ON_HOLD,
        )

        self.assertFalse(result.success)
        self.assertEqual(
            self.repo.get_project(project_id).status,
            ProjectStatus.ACTIVE,
        )

    def test_archived_client_cannot_update_project_status(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח בארכיון לעדכון",
                phone="050-5558989",
                email="archived-status@example.com",
            )
        )
        project_id = self.repo.create_project(
            Project(client_id=client_id, project_name="פרויקט היסטורי")
        )
        self.repo.archive_client(client_id)

        result = self.customers.update_project_status(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            project_id,
            ProjectStatus.ON_HOLD,
        )

        self.assertFalse(result.success)
        self.assertEqual(
            self.repo.get_project(project_id).status,
            ProjectStatus.ACTIVE,
        )

    def test_cannot_update_project_to_same_status(self) -> None:
        client_id = self.repo.create_client(
            Client(
                name="לקוח סטטוס זהה",
                phone="050-5559090",
                email="same-status@example.com",
            )
        )
        project_id = self.repo.create_project(
            Project(client_id=client_id, project_name="פרויקט פעיל")
        )

        result = self.customers.update_project_status(
            RoleEnum.OFFICE_MANAGER,
            client_id,
            project_id,
            ProjectStatus.ACTIVE,
        )

        self.assertFalse(result.success)



class TestDecisions(RokitnaTestCase):
    def _architect_id(self) -> int:
        architect = self.repo.find_user_by_username("architect")
        self.assertIsNotNone(architect)
        return architect.user_id

    def test_save_decision(self) -> None:
        project_id = self._create_project()
        result = self.decisions.save_decision(
            RoleEnum.ARCHITECT,
            self._architect_id(),
            project_id,
            "להשתמש בתאורה חמה",
        )
        self.assertTrue(result.success)
        self.assertIn("decision_id", result.data)
        self.assertIn("change_id", result.data)

        decisions = self.repo.list_decisions_by_project(project_id)
        changes = self.repo.list_changes_by_project(project_id)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(len(changes), 1)
        self.assertEqual(decisions[0].created_by_user_id, self._architect_id())
        self.assertEqual(changes[0].created_by_user_id, self._architect_id())
        self.assertEqual(changes[0].decision_id, decisions[0].decision_id)
        self.assertIsNotNone(decisions[0].created_at)
        self.assertIsNotNone(changes[0].created_at)

    def test_save_decision_empty_text(self) -> None:
        project_id = self._create_project()
        result = self.decisions.save_decision(
            RoleEnum.ARCHITECT,
            self._architect_id(),
            project_id,
            "  ",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.data["state"], "invalid")

    def test_office_manager_cannot_record_decision(self) -> None:
        project_id = self._create_project()
        manager = self.repo.find_user_by_username("manager")
        result = self.decisions.save_decision(
            RoleEnum.OFFICE_MANAGER,
            manager.user_id,
            project_id,
            "החלטה ללא הרשאה",
        )
        self.assertFalse(result.success)
        self.assertEqual(self.repo.list_decisions_by_project(project_id), [])

    def test_decision_actor_role_mismatch_is_rejected(self) -> None:
        project_id = self._create_project()
        manager = self.repo.find_user_by_username("manager")
        result = self.decisions.save_decision(
            RoleEnum.ARCHITECT,
            manager.user_id,
            project_id,
            "ניסיון זיוף תפקיד",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.data["state"], "invalid")

    def test_list_changes_for_project(self) -> None:
        project_id = self._create_project()
        self.decisions.save_decision(
            RoleEnum.ARCHITECT,
            self._architect_id(),
            project_id,
            "החלטה להצגת היסטוריה",
        )
        result = self.decisions.list_changes(RoleEnum.ARCHITECT, project_id)
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)


class TestReports(RokitnaTestCase):
    def test_generate_management_report(self) -> None:
        """The management report aggregates the active projects and is saved."""
        self._create_project()  # an active project
        result = self.reports.generate_management_report(
            RoleEnum.OFFICE_MANAGER, "active_projects"
        )
        self.assertTrue(result.success)
        report: Report = result.data
        self.assertEqual(report.report_type, ReportType.MANAGEMENT)
        self.assertEqual(report.status, ReportStatus.SAVED)
        # Four sections: projects, milestones, payments, alerts.
        self.assertEqual(len(report.sections), 4)
        # The active project appears in the projects section.
        self.assertGreaterEqual(len(report.sections[0].rows), 1)
        # The generation was recorded in the database with a timestamp.
        history = self.repo.list_reports()
        self.assertEqual(len(history), 1)
        self.assertIsNotNone(history[0].generated_at)

    def test_generate_report_rejects_missing_criteria(self) -> None:
        result = self.reports.generate_management_report(
            RoleEnum.OFFICE_MANAGER, ""
        )
        self.assertFalse(result.success)
        self.assertEqual(self.repo.list_reports(), [])

    def test_generate_report_rejects_unknown_criteria(self) -> None:
        result = self.reports.generate_management_report(
            RoleEnum.OFFICE_MANAGER, "does_not_exist"
        )
        self.assertFalse(result.success)

    def test_management_report_collects_only_active_projects(self) -> None:
        """Completed/on-hold projects must not appear in the management report."""
        client_id = self.repo.create_client(
            Client(name="לקוח", phone="0500000001", email="active-only@example.com")
        )
        active_id = self.repo.create_project(
            Project(client_id=client_id, project_name="פעיל", status=ProjectStatus.ACTIVE)
        )
        self.repo.create_project(
            Project(
                client_id=client_id,
                project_name="הושלם",
                status=ProjectStatus.COMPLETED,
            )
        )

        result = self.reports.generate_management_report(
            RoleEnum.OFFICE_MANAGER, "active_projects"
        )
        self.assertTrue(result.success)
        project_ids = {row[0] for row in result.data.sections[0].rows}
        self.assertIn(str(active_id), project_ids)
        self.assertEqual(len(result.data.sections[0].rows), 1)

    def test_export_report_csv(self) -> None:
        self._create_project()
        report = self.reports.generate_management_report(
            RoleEnum.OFFICE_MANAGER, "active_projects"
        ).data
        path = self.reports.export_to_csv(report)
        self.assertTrue(Path(path).exists())


class TestEdgeCases(RokitnaTestCase):
    """Boundary conditions and uncommon-but-possible inputs."""

    def test_login_trims_whitespace_in_username(self) -> None:
        result = self.auth.login("  manager  ", "1234")
        self.assertTrue(result.success)

    def test_login_unknown_username(self) -> None:
        result = self.auth.login("ghost", "1234")
        self.assertFalse(result.success)

    def test_duplicate_email_is_case_insensitive(self) -> None:
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "א", "050-1000001", "Dana@Example.com"
        )
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "ב", "050-1000002", "dana@example.com"
        )
        self.assertFalse(result.success)

    def test_update_nonexistent_client(self) -> None:
        result = self.customers.update_client(
            RoleEnum.OFFICE_MANAGER,
            9999,
            "אף אחד",
            "050-9000000",
            "none@example.com",
        )
        self.assertFalse(result.success)

    def test_delete_nonexistent_client(self) -> None:
        result = self.customers.delete_client(RoleEnum.OFFICE_MANAGER, 9999)
        self.assertFalse(result.success)

    def test_update_to_phone_owned_by_another_client(self) -> None:
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "ראשון", "050-1111111", "first@example.com"
        )
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "שני", "050-2222222", "second@example.com"
        )
        first, second = self.repo.list_clients()[1], self.repo.list_clients()[0]
        # Try to give 'second' the phone already owned by 'first'.
        result = self.customers.update_client(
            RoleEnum.OFFICE_MANAGER,
            second.client_id,
            second.name,
            first.phone,
            second.email,
        )
        self.assertFalse(result.success)

    def test_update_same_client_keeps_its_own_phone(self) -> None:
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "יחיד", "050-3333333", "only@example.com"
        )
        client = self.repo.list_clients()[0]
        # Re-saving the same client with its own phone/email must succeed.
        result = self.customers.update_client(
            RoleEnum.OFFICE_MANAGER,
            client.client_id,
            "יחיד מעודכן",
            client.phone,
            client.email,
        )
        self.assertTrue(result.success)

    def test_create_client_missing_name(self) -> None:
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "   ", "050-4444444", "noname@example.com"
        )
        self.assertFalse(result.success)

    def test_create_client_invalid_phone(self) -> None:
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "טל", "abc", "phone@example.com"
        )
        self.assertFalse(result.success)

    def test_save_decision_nonexistent_project(self) -> None:
        architect = self.repo.find_user_by_username("architect")
        result = self.decisions.save_decision(
            RoleEnum.ARCHITECT, architect.user_id, 9999, "החלטה כלשהי"
        )
        self.assertFalse(result.success)

    def test_generate_report_on_empty_database(self) -> None:
        """With no active projects the report still generates, with empty rows."""
        result = self.reports.generate_management_report(
            RoleEnum.OFFICE_MANAGER, "active_projects"
        )
        self.assertTrue(result.success)
        for section in result.data.sections:
            self.assertEqual(section.rows, [])

    def test_duplicate_phone_detected_across_formats(self) -> None:
        """A number entered with and without separators is the same client."""
        self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "ראשון", "050-1234567", "fmt1@example.com"
        )
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "שני", "0501234567", "fmt2@example.com"
        )
        self.assertFalse(result.success)

    def test_long_decision_text_is_accepted(self) -> None:
        project_id = self._create_project()
        long_text = "פירוט " * 500
        architect = self.repo.find_user_by_username("architect")
        result = self.decisions.save_decision(
            RoleEnum.ARCHITECT, architect.user_id, project_id, long_text
        )
        self.assertTrue(result.success)

    def test_management_report_is_repeatable(self) -> None:
        """Generating the report twice records two history rows."""
        self._create_project()
        for _ in range(2):
            result = self.reports.generate_management_report(
                RoleEnum.OFFICE_MANAGER, "active_projects"
            )
            self.assertTrue(result.success)
        self.assertEqual(len(self.repo.list_reports()), 2)


class TestDecisionAtomicPersistence(RokitnaTestCase):
    def test_atomic_save_rolls_back_when_history_cannot_be_saved(self) -> None:
        """A failed audit insert must not leave an orphan decision record."""
        project_id = self._create_project()
        decision = DecisionLog(
            project_id=project_id,
            created_by_user_id=self.repo.find_user_by_username("architect").user_id,
            decision_text="החלטה שאמורה להתגלגל אחורה",
        )
        # Invalid author id makes the second INSERT violate the fresh-schema FK.
        history = ChangeHistory(
            project_id=project_id,
            created_by_user_id=999999,
            description="רשומת היסטוריה לא תקינה",
        )

        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.save_decision_with_history(decision, history)

        self.assertEqual(self.repo.list_decisions_by_project(project_id), [])
        self.assertEqual(self.repo.list_changes_by_project(project_id), [])


class TestDecisionEntrySession(unittest.TestCase):
    def test_state_machine_transitions(self) -> None:
        entry = DecisionEntrySession()
        self.assertEqual(entry.status, DecisionEntryStatus.DRAFT)

        entry.mark_invalid("חסר טקסט")
        self.assertEqual(entry.status, DecisionEntryStatus.INVALID)
        entry.return_to_draft()
        entry.begin_saving()
        self.assertEqual(entry.status, DecisionEntryStatus.SAVING)
        entry.mark_recorded()
        self.assertEqual(entry.status, DecisionEntryStatus.RECORDED)
        entry.close()
        self.assertEqual(entry.status, DecisionEntryStatus.CLOSED)

    def test_save_failure_can_return_to_draft(self) -> None:
        entry = DecisionEntrySession()
        entry.begin_saving()
        entry.mark_save_failed("תקלה")
        self.assertEqual(entry.status, DecisionEntryStatus.SAVE_FAILED)
        entry.return_to_draft()
        self.assertEqual(entry.status, DecisionEntryStatus.DRAFT)


class TestClientPortal(RokitnaTestCase):
    """Client self-service portal: projects, meetings and inquiries."""

    def setUp(self) -> None:
        super().setUp()
        self.client_ctrl = ClientController(self.repo)
        self.client_id = self.repo.create_client(
            Client(name="לקוח פורטל", phone="0501112233", email="portal@example.com")
        )
        self.client_user = User(
            username="client",
            password_hash="x",
            role=RoleEnum.CLIENT,
            user_id=99,
            client_id=self.client_id,
        )

    def test_client_views_own_projects(self) -> None:
        self.repo.create_project(
            Project(client_id=self.client_id, project_name="הפרויקט שלי")
        )
        result = self.client_ctrl.view_my_projects(self.client_user)
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].project_name, "הפרויקט שלי")

    def test_client_sees_only_own_projects(self) -> None:
        other_id = self.repo.create_client(
            Client(name="אחר", phone="0502223344", email="other@example.com")
        )
        self.repo.create_project(Project(client_id=other_id, project_name="של אחר"))
        self.repo.create_project(
            Project(client_id=self.client_id, project_name="שלי")
        )
        result = self.client_ctrl.view_my_projects(self.client_user)
        self.assertEqual(len(result.data), 1)
        self.assertEqual(result.data[0].project_name, "שלי")

    def test_unlinked_client_cannot_view_projects(self) -> None:
        unlinked = User(
            username="ghost", password_hash="x", role=RoleEnum.CLIENT, client_id=None
        )
        result = self.client_ctrl.view_my_projects(unlinked)
        self.assertFalse(result.success)

    def test_client_submits_and_lists_inquiry(self) -> None:
        result = self.client_ctrl.submit_inquiry(self.client_user, "מתי הפגישה הבאה?")
        self.assertTrue(result.success)
        listing = self.client_ctrl.list_my_inquiries(self.client_user)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0].content, "מתי הפגישה הבאה?")

    def test_client_empty_inquiry_rejected(self) -> None:
        result = self.client_ctrl.submit_inquiry(self.client_user, "   ")
        self.assertFalse(result.success)
        self.assertEqual(self.repo.list_inquiries_by_client(self.client_id), [])

    def test_manager_cannot_submit_inquiry(self) -> None:
        manager_user = User(
            username="manager",
            password_hash="x",
            role=RoleEnum.OFFICE_MANAGER,
            client_id=self.client_id,
        )
        result = self.client_ctrl.submit_inquiry(manager_user, "לא אמור לעבוד")
        self.assertFalse(result.success)


class TestMeetings(RokitnaTestCase):
    """Office manager schedules meetings the client then sees."""

    def setUp(self) -> None:
        super().setUp()
        self.client_ctrl = ClientController(self.repo)
        self.client_id = self.repo.create_client(
            Client(name="לקוח פגישות", phone="0503334455", email="meet@example.com")
        )
        self.project_id = self.repo.create_project(
            Project(client_id=self.client_id, project_name="פרויקט פגישות")
        )
        self.client_user = User(
            username="client",
            password_hash="x",
            role=RoleEnum.CLIENT,
            client_id=self.client_id,
        )

    def test_manager_schedules_meeting_client_sees_it(self) -> None:
        result = self.customers.schedule_meeting(
            RoleEnum.OFFICE_MANAGER,
            self.client_id,
            self.project_id,
            "2099-01-01",
            "10:30",
            "משרד",
            "פגישת תיאום",
        )
        self.assertTrue(result.success)
        upcoming = self.client_ctrl.view_my_meetings(self.client_user)
        self.assertEqual(len(upcoming.data), 1)
        self.assertEqual(upcoming.data[0].summary, "פגישת תיאום")

    def test_past_meeting_not_in_upcoming(self) -> None:
        self.customers.schedule_meeting(
            RoleEnum.OFFICE_MANAGER,
            self.client_id,
            self.project_id,
            "2000-01-01",
            "10:30",
            "משרד",
            "פגישה שעברה",
        )
        upcoming = self.client_ctrl.view_my_meetings(self.client_user)
        self.assertEqual(upcoming.data, [])

    def test_client_cannot_schedule_meeting(self) -> None:
        result = self.customers.schedule_meeting(
            RoleEnum.CLIENT,
            self.client_id,
            self.project_id,
            "2099-01-01",
            "10:30",
            "משרד",
            "ניסיון",
        )
        self.assertFalse(result.success)

    def test_meeting_rejected_for_foreign_project(self) -> None:
        other_id = self.repo.create_client(
            Client(name="אחר", phone="0504445566", email="foreign@example.com")
        )
        foreign_project = self.repo.create_project(
            Project(client_id=other_id, project_name="של אחר")
        )
        result = self.customers.schedule_meeting(
            RoleEnum.OFFICE_MANAGER,
            self.client_id,
            foreign_project,
            "2099-01-01",
            "10:30",
            "משרד",
            "לא תקין",
        )
        self.assertFalse(result.success)

    def test_schedule_meeting_requires_fields(self) -> None:
        result = self.customers.schedule_meeting(
            RoleEnum.OFFICE_MANAGER,
            self.client_id,
            self.project_id,
            "2099-01-01",
            "10:30",
            "   ",
            "נושא",
        )
        self.assertFalse(result.success)


class TestClientAccountProvisioning(RokitnaTestCase):
    def test_create_client_provisions_login_account(self) -> None:
        result = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "דנה כהן", "0501230001", "dana.k@example.com"
        )
        self.assertTrue(result.success)
        self.assertIn("username", result.data)
        self.assertTrue(len(result.data["password"]) >= 8)
        # The generated account can log in and is linked to the new client.
        login = self.auth.login(result.data["username"], result.data["password"])
        self.assertTrue(login.success)
        self.assertEqual(login.data.role, RoleEnum.CLIENT)
        self.assertEqual(login.data.client_id, result.data["client_id"])

    def test_deleting_client_removes_its_account(self) -> None:
        created = self.customers.create_client(
            RoleEnum.OFFICE_MANAGER, "למחיקה", "0501230002", "del.acct@example.com"
        )
        client_id = created.data["client_id"]
        username = created.data["username"]
        self.assertTrue(
            self.customers.delete_client(RoleEnum.OFFICE_MANAGER, client_id).success
        )
        self.assertIsNone(self.repo.find_user_by_username(username))


class TestArchitectWorkspace(RokitnaTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.arch = ArchitectController(self.repo)
        self.architect_user = User(
            username="architect",
            password_hash="x",
            role=RoleEnum.ARCHITECT,
            user_id=self.repo.find_user_by_username("architect").user_id,
        )
        self.project_id = self._create_project()

    def test_architect_adds_field_note(self) -> None:
        res = self.arch.add_field_note(self.architect_user, self.project_id, "הערת שטח")
        self.assertTrue(res.success)
        self.assertEqual(len(self.repo.list_field_notes_by_project(self.project_id)), 1)

    def test_architect_uploads_drawing(self) -> None:
        res = self.arch.upload_drawing(
            self.architect_user, self.project_id, "plan.pdf", b"DATA", "תוכנית"
        )
        self.assertTrue(res.success)
        self.assertEqual(len(self.repo.list_drawings_by_project(self.project_id)), 1)

    def test_architect_documents_change(self) -> None:
        res = self.arch.document_change(
            self.architect_user, self.project_id, "שינוי חלון", 2500.0
        )
        self.assertTrue(res.success)
        changes = self.repo.list_project_changes_by_project(self.project_id)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].status.value, "Pending")

    def test_manager_cannot_use_architect_workspace(self) -> None:
        manager_user = User(
            username="manager", password_hash="x", role=RoleEnum.OFFICE_MANAGER,
            user_id=1,
        )
        res = self.arch.add_field_note(manager_user, self.project_id, "לא מורשה")
        self.assertFalse(res.success)

    def test_empty_field_note_rejected(self) -> None:
        res = self.arch.add_field_note(self.architect_user, self.project_id, "  ")
        self.assertFalse(res.success)


class TestClientApprovals(RokitnaTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.arch = ArchitectController(self.repo)
        self.clients_ctrl = ClientController(self.repo)
        self.client_id = self.repo.create_client(
            Client(name="לקוח אישורים", phone="0505550001", email="approve@example.com")
        )
        self.project_id = self.repo.create_project(
            Project(client_id=self.client_id, project_name="פרויקט אישורים")
        )
        self.architect_user = User(
            username="architect", password_hash="x", role=RoleEnum.ARCHITECT,
            user_id=self.repo.find_user_by_username("architect").user_id,
        )
        self.client_user = User(
            username="client", password_hash="x", role=RoleEnum.CLIENT,
            user_id=50, client_id=self.client_id,
        )

    def test_client_approves_change(self) -> None:
        change_id = self.arch.document_change(
            self.architect_user, self.project_id, "שינוי", 1000.0
        ).data
        res = self.clients_ctrl.decide_change(self.client_user, change_id, True)
        self.assertTrue(res.success)
        self.assertEqual(self.repo.get_change(change_id).status.value, "Approved")

    def test_client_rejects_change(self) -> None:
        change_id = self.arch.document_change(
            self.architect_user, self.project_id, "שינוי", 1000.0
        ).data
        res = self.clients_ctrl.decide_change(self.client_user, change_id, False)
        self.assertTrue(res.success)
        self.assertEqual(self.repo.get_change(change_id).status.value, "Rejected")

    def test_client_cannot_decide_foreign_change(self) -> None:
        other_client = self.repo.create_client(
            Client(name="אחר", phone="0505550002", email="foreign-c@example.com")
        )
        other_project = self.repo.create_project(
            Project(client_id=other_client, project_name="של אחר")
        )
        change_id = self.arch.document_change(
            self.architect_user, other_project, "שינוי זר", 500.0
        ).data
        res = self.clients_ctrl.decide_change(self.client_user, change_id, True)
        self.assertFalse(res.success)

    def test_client_confirms_meeting(self) -> None:
        meeting_id = self.customers.schedule_meeting(
            RoleEnum.OFFICE_MANAGER, self.client_id, self.project_id,
            "2099-01-01", "10:00", "משרד", "פגישה",
        ).data
        res = self.clients_ctrl.confirm_meeting(self.client_user, meeting_id)
        self.assertTrue(res.success)
        self.assertEqual(self.repo.get_meeting(meeting_id).status.value, "Confirmed")

    def test_client_targets_inquiry_to_architect(self) -> None:
        res = self.clients_ctrl.submit_inquiry(
            self.client_user, "שאלה לאדריכלית", RoleEnum.ARCHITECT.value
        )
        self.assertTrue(res.success)
        inquiries = self.repo.list_inquiries_by_target_role(RoleEnum.ARCHITECT.value)
        self.assertEqual(len(inquiries), 1)


class TestManagerReminticsAndOversight(RokitnaTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.manager_ctrl = ManagerController(self.repo)
        self.manager_user = User(
            username="manager", password_hash="x", role=RoleEnum.OFFICE_MANAGER,
            user_id=self.repo.find_user_by_username("manager").user_id,
        )
        self.client_id = self.repo.create_client(
            Client(name="לקוח", phone="0506660001", email="rem@example.com")
        )

    def test_reminder_to_client(self) -> None:
        res = self.manager_ctrl.send_reminder_to_client(
            self.manager_user, self.client_id, "תזכורת"
        )
        self.assertTrue(res.success)
        self.assertEqual(len(self.repo.list_reminders_for_client(self.client_id)), 1)

    def test_reminder_to_architects(self) -> None:
        res = self.manager_ctrl.send_reminder_to_architects(self.manager_user, "תזכורת")
        self.assertTrue(res.success)
        self.assertEqual(
            len(self.repo.list_reminders_for_role(RoleEnum.ARCHITECT.value)), 1
        )

    def test_architect_cannot_send_reminders(self) -> None:
        architect_user = User(
            username="architect", password_hash="x", role=RoleEnum.ARCHITECT, user_id=2,
        )
        res = self.manager_ctrl.send_reminder_to_architects(architect_user, "x")
        self.assertFalse(res.success)

    def test_oversight_lists_activity(self) -> None:
        res = self.manager_ctrl.list_architect_activity(RoleEnum.OFFICE_MANAGER)
        self.assertTrue(res.success)
        self.assertIn("field_notes", res.data)
        self.assertIn("drawings", res.data)
        self.assertIn("changes", res.data)

    def test_client_cannot_view_oversight(self) -> None:
        res = self.manager_ctrl.list_architect_activity(RoleEnum.CLIENT)
        self.assertFalse(res.success)


class TestFinancialReport(RokitnaTestCase):
    def test_financial_report_breaks_down_costs(self) -> None:
        client_id = self.repo.create_client(
            Client(name="לקוח פיננסי", phone="0507770001", email="fin@example.com")
        )
        project_id = self.repo.create_project(
            Project(client_id=client_id, project_name="פרויקט פיננסי")
        )
        req_id = self.repo.create_payment_request(
            PaymentRequest(project_id=project_id, amount=10000.0, description="תכנון")
        )
        self.repo.create_payment(Payment(request_id=req_id, amount=4000.0))

        result = self.reports.generate_financial_report(
            RoleEnum.OFFICE_MANAGER, "active_projects"
        )
        self.assertTrue(result.success)
        titles = [s.title for s in result.data.sections]
        self.assertIn("עלויות לפי חלקי הפרויקט", titles)
        self.assertIn("סיכום פיננסי", titles)
        # The parts section has our one payment request.
        parts = result.data.sections[0]
        self.assertEqual(len(parts.rows), 1)

    def test_financial_report_permission_denied_for_client(self) -> None:
        result = self.reports.generate_financial_report(
            RoleEnum.CLIENT, "active_projects"
        )
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
