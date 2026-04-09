from .models import JournalConfig


def journal_config(request):
    return {'journal': JournalConfig.get()}
