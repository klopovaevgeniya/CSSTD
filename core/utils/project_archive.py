from django.db.models import Q


import logging

logger = logging.getLogger(__name__)

# Summary: Содержит логику для archived project q.
def archived_project_q(prefix=''):
    field_name = f'{prefix}__status__name' if prefix else 'status__name'
    return (
        Q(**{f'{field_name}__icontains': 'закры'})
        | Q(**{f'{field_name}__icontains': 'выполн'})
        | Q(**{f'{field_name}__icontains': 'заверш'})
    )


# Summary: Содержит логику для not archived project q.
def not_archived_project_q(prefix=''):
    return ~archived_project_q(prefix=prefix)
