import hashlib

import pytest

from customs_ai.parsers.errors import FileCorruptedError
from customs_ai.parsers.excel import XlsParser


xlrd = pytest.importorskip("xlrd")
xlwt = pytest.importorskip("xlwt")


def _build_xls(path):
    workbook = xlwt.Workbook()
    first = workbook.add_sheet("First")
    first.write(0, 0, "Legacy")
    first.write(1, 1, 42.5)
    first.write_merge(3, 3, 0, 2, "Merged")
    second = workbook.add_sheet("Second")
    second.write(0, 0, "测试")
    workbook.save(str(path))


def _cell(sheet, coordinate):
    return next(cell for cell in sheet.cells if cell.coordinate == coordinate)


def test_xls_basic_cells_sheet_order_and_merged_ranges(tmp_path):
    path = tmp_path / "legacy.xls"
    _build_xls(path)

    parsed = XlsParser().parse("DOC-XLS", path)

    assert parsed.file_type == "xls"
    assert parsed.parser_used == "xlrd"
    assert [sheet.name for sheet in parsed.sheets] == ["First", "Second"]
    assert _cell(parsed.sheets[0], "A1").raw_value == "Legacy"
    assert _cell(parsed.sheets[0], "B2").raw_value == 42.5
    assert "A4:C4" in parsed.sheets[0].merged_ranges
    assert _cell(parsed.sheets[1], "A1").raw_value == "测试"


def test_corrupt_xls_is_rejected(tmp_path):
    path = tmp_path / "bad.xls"
    path.write_bytes(b"not a biff workbook")

    with pytest.raises(FileCorruptedError) as exc:
        XlsParser().parse("DOC-BAD-XLS", path)
    assert exc.value.code == "FILE_CORRUPTED"


def test_xls_source_file_remains_unchanged(tmp_path):
    path = tmp_path / "immutable.xls"
    _build_xls(path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    XlsParser().parse("DOC-HASH-XLS", path)

    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
