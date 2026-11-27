"""Adds the Butter & Bean scenario on top of the upstream demo data.

    python manage.py demo_data --reset          # upstream demo data first
    python tests/team/seed/seed_butter_bean.py  # then the team scenario

Safe to run more than once: existing users, queues and tickets are reused.
The upstream demo accounts and tickets stay as they are, so the performance
runs (which use them) are not affected.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demodesk.config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from helpdesk.models import Queue, Ticket  # noqa: E402
from tests.team.seed import content  # noqa: E402

User = get_user_model()


def user(username, first, last, staff):
    account, created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}@{content.DOMAIN}"
            if not staff else f"{username}@{content.DOMAIN}",
            "is_staff": staff,
        },
    )
    if created:
        account.set_password(content.PASSWORD)
        account.save()
    return account


def main():
    staff = {u: user(u, f, l, True) for u, f, l, _role in content.STAFF}
    user(*content.CUSTOMER, staff=False)
    user(*content.SECOND_CUSTOMER, staff=False)

    queues = {}
    for title, slug, email in content.QUEUES:
        queues[slug], _ = Queue.objects.get_or_create(
            slug=slug,
            defaults={"title": title, "email_address": email, "allow_public_submission": True},
        )

    created = 0
    for slug, title, description, submitter, owner, status, priority in content.TICKETS:
        _, new = Ticket.objects.get_or_create(
            queue=queues[slug],
            title=title,
            defaults={
                "description": description,
                "submitter_email": submitter,
                "assigned_to": staff[owner],
                "status": status,
                "priority": priority,
            },
        )
        created += new
    print(f"Butter & Bean: {len(staff) + 2} people, {len(queues)} queues, {created} new tickets")


if __name__ == "__main__":
    main()
