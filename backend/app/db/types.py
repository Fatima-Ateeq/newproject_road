from enum import Enum

from sqlalchemy import Enum as SqlEnum


def enum_type(enum_class: type[Enum]) -> SqlEnum:
    """Store an Enum as readable text (for example 'Under Review') in any database."""
    return SqlEnum(
        enum_class,
        native_enum=False,
        length=32,
        values_callable=lambda members: [member.value for member in members],
    )
