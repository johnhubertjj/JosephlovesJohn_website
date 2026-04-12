#!/usr/bin/env python3
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    """Run administrative tasks for the Django project.

    :returns: ``None``.
    :raises ImportError: If Django is not installed in the active environment.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "josephlovesjohn_site.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed. Install dependencies and try again."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
