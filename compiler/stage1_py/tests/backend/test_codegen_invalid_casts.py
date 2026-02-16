#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2026 gwz

import pytest

from l0_backend import Backend
from l0_driver import L0Driver


def test_codegen_rejects_invalid_casts(tmp_path, write_l0_file, search_paths):
    write_l0_file(
        "badcast",
        """
        module badcast;

        func main() -> int {
            return "hello" as int;
        }
        """,
    )

    driver = L0Driver(search_paths=search_paths)
    result = driver.analyze("badcast")
    assert result.has_errors()

    with pytest.raises(ValueError):
        Backend(result).generate()
