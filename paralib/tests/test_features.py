import pytest
from paralib.vault import extract_structured_features_from_note

def test_extract_features_okrs():
    note = """
    ---
    status: Backlog
    tags: [OKR, KPIs]
    ---
    ## OKR 1: Excelencia Operacional
    - [ ] Tarea 1
    """
    features = extract_structured_features_from_note(note)
    assert features['has_okr']['value'] is True
    assert features['n_tasks']['value'] == 1
    assert features['status']['value'] == 'Backlog' 