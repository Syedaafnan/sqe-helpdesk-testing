"""Access matrix checks in the browser (final report, Security, matrix rows AC-x).

Roles: anonymous visitor, customer (baidar, not staff), staff (arooj; haider for the no-permission check,
staff but not superuser). Each test checks one cell of the matrix.
"""

import pytest

from tests.team.seed import content as cafe

from .conftest import login, submit_staff, unique


def api_status(page, path):
    """Status of an API call made with the browser's own session cookie."""
    return page.request.get(path).status


def test_ac01_anonymous_redirected_from_ticket_list(page):
    page.goto("/tickets/")
    assert "/login/" in page.url


def test_ac02_anonymous_denied_on_api(page):
    page.goto("/")
    assert api_status(page, "/api/tickets/") in (401, 403)


def test_ac03_customer_redirected_from_reports(page):
    login(page, cafe.CUSTOMER[0])
    page.goto("/reports/")
    assert "/login/" in page.url


def test_ac04_customer_session_denied_on_staff_api(page):
    login(page, cafe.CUSTOMER[0])
    assert api_status(page, "/api/tickets/") == 403
    assert api_status(page, "/api/followups/") == 403


def test_ac05_customer_redirected_from_admin(page):
    login(page, cafe.CUSTOMER[0])
    page.goto("/admin/")
    assert "/admin/login/" in page.url


def test_ac06_staff_without_permission_cannot_manage_users(page):
    login(page, cafe.LIMITED_STAFF)
    response = page.goto("/admin/auth/user/")
    assert response.status == 403 or "/admin/login/" in page.url


def test_ac07_staff_can_use_ticket_list_and_api(page):
    login(page, cafe.W2_STAFF)
    page.goto("/tickets/")
    assert page.url.endswith("/tickets/")
    assert api_status(page, "/api/tickets/") == 200


def test_ac08_customer_cannot_reach_email_ignore_list(page):
    login(page, cafe.CUSTOMER[0])
    response = page.goto("/ignore/")
    assert response.status == 403 or "/login/" in page.url
    assert page.get_by_text("E-Mail Ignore").count() == 0


def test_ac10_customer_redirected_from_staff_ticket_page(page, new_page):
    login(page, cafe.W2_STAFF)
    ticket_id = submit_staff(page, unique("Staff only: supplier invoice"))
    customer = new_page()
    login(customer, cafe.CUSTOMER[0])
    customer.goto(f"/tickets/{ticket_id}/")
    assert "/login/" in customer.url


@pytest.mark.xfail(strict=True, reason="DEF-09: /system_settings/ only requires login, not staff")
def test_ac09_customer_does_not_see_system_settings(page):
    login(page, cafe.CUSTOMER[0])
    page.goto("/system_settings/")
    assert page.get_by_text("Maintain Queues").count() == 0
