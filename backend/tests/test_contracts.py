from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.contracts import TareaInput, ComentarioInput, ComentarioOut


@pytest.mark.parametrize('data', [
    {'titulo': '  '}, {'titulo': 'x' * 201}, {'descripcion': 'x' * 5001},
    {'estado': 'asignada'}, {'solicitante_id': 1}, {'materia_id': 0},
    {'presupuesto': '1.001'}, {'presupuesto': '-1'}, {'presupuesto': 'NaN'},
    {'presupuesto': 'Infinity'}, {'presupuesto': '10000000000'}, {'presupuesto': True},
    {'fecha_limite': '2026-10-18T00:00:00Z'}, {'fecha_limite': 123},
    {'fecha_limite': '2026-02-30'},
])
def test_reject_invalid_task(data):
    with pytest.raises(ValidationError):
        TareaInput(**data)


def test_draft_and_money():
    assert TareaInput().model_dump(exclude_unset=True) == {}
    assert TareaInput(titulo=None).model_dump(exclude_unset=True) == {'titulo': None}
    assert TareaInput(presupuesto='0', titulo='  Hola  ').model_dump(mode='json')['presupuesto'] == '0.00'
    assert TareaInput(presupuesto='9999999999.99').model_dump(mode='json')['presupuesto'] == '9999999999.99'
    assert TareaInput(fecha_limite='2000-01-01').fecha_limite.year == 2000


def test_comment_and_utc():
    with pytest.raises(ValidationError):
        ComentarioInput(contenido='  ')
    item = ComentarioOut(id=1, contenido='Texto', fecha=datetime(2026, 1, 1),
                         autor={'id': 1, 'rol': 'solicitante', 'nombre': 'Uno'}, requiere_correccion=False)
    assert item.model_dump(mode='json')['fecha'] == '2026-01-01T00:00:00Z'
