"""U001-T3"""
import pytest
from pydantic import ValidationError

from app.models import LogFileInfo, MetricGroup, Series


def test_camelCaseで直列化される():
    info = LogFileInfo(
        fileId="x", fileName="sar23", kind="sar", date="2026-08-23", sizeBytes=10
    )
    dumped = info.model_dump(mode="json")
    assert set(dumped) == {"fileId", "fileName", "kind", "date", "sizeBytes", "hostname"}


def test_valuesにNoneを含められる():
    s = Series(key=None, metric="%usr", unit="%", values=[1.0, None])
    assert s.values == [1.0, None]


def test_必須フィールド欠落でバリデーションエラー():
    with pytest.raises(ValidationError):
        MetricGroup(groupId="MG-CPU", keyLabel=None)
