#  SPDX-License-Identifier: MIT OR Apache-2.0
#  Copyright (c) 2025-2026 gwz

import os
from dataclasses import dataclass
from typing import Optional

from l0_ast import Node
from l0_lexer import Token


DIAGNOSTIC_CODE_FAMILIES = {
    "LEX": [
        "LEX-0010",
        "LEX-0020",
        "LEX-0021",
        "LEX-0030",
        "LEX-0040",
        "LEX-0050",
        "LEX-0051",
        "LEX-0052",
        "LEX-0053",
        "LEX-0059",
        "LEX-0060",
        "LEX-0070",
    ],
    "PAR": [
        "PAR-0010",
        "PAR-0011",
        "PAR-0020",
        "PAR-0030",
        "PAR-0040",
        "PAR-0041",
        "PAR-0042",
        "PAR-0043",
        "PAR-0044",
        "PAR-0045",
        "PAR-0046",
        "PAR-0050",
        "PAR-0051",
        "PAR-0052",
        "PAR-0053",
        "PAR-0054",
        "PAR-0055",
        "PAR-0056",
        "PAR-0060",
        "PAR-0061",
        "PAR-0062",
        "PAR-0063",
        "PAR-0064",
        "PAR-0065",
        "PAR-0066",
        "PAR-0067",
        "PAR-0068",
        "PAR-0070",
        "PAR-0071",
        "PAR-0072",
        "PAR-0073",
        "PAR-0080",
        "PAR-0081",
        "PAR-0082",
        "PAR-0083",
        "PAR-0090",
        "PAR-0091",
        "PAR-0100",
        "PAR-0110",
        "PAR-0111",
        "PAR-0112",
        "PAR-0120",
        "PAR-0121",
        "PAR-0122",
        "PAR-0130",
        "PAR-0131",
        "PAR-0132",
        "PAR-0140",
        "PAR-0141",
        "PAR-0142",
        "PAR-0143",
        "PAR-0144",
        "PAR-0150",
        "PAR-0160",
        "PAR-0161",
        "PAR-0170",
        "PAR-0171",
        "PAR-0172",
        "PAR-0173",
        "PAR-0174",
        "PAR-0175",
        "PAR-0176",
        "PAR-0177",
        "PAR-0180",
        "PAR-0181",
        "PAR-0182",
        "PAR-0190",
        "PAR-0200",
        "PAR-0210",
        "PAR-0211",
        "PAR-0212",
        "PAR-0223",
        "PAR-0224",
        "PAR-0225",
        "PAR-0300",
        "PAR-0310",
        "PAR-0311",
        "PAR-0312",
        "PAR-0320",
        "PAR-0321",
        "PAR-0400",
        "PAR-9401",
    ],
    "DRV": [
        "DRV-0010",
        "DRV-0020",
        "DRV-0030",
    ],
}


@dataclass
class Diagnostic:
    kind: str  # "error" or "warning"
    message: str
    module_name: Optional[str] = None  # module name
    filename: Optional[str] = None  # file path

    # Primary location (start of the span)
    line: Optional[int] = None
    column: Optional[int] = None

    # Optional end of span (exclusive)
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    # Return the one-line header; snippets will be printed at the call site
    def format(self) -> str:
        loc = ""
        if self.filename is not None:
            loc += f"{os.path.abspath(str(self.filename))}"
        if self.line is not None:
            loc += f":{self.line}"
            if self.column is not None:
                loc += f":{self.column}"
            if self.module_name is not None:
                loc += f"({self.module_name})"
        if loc:
            loc += ": "
        return f"{loc}{self.kind}: {self.message}"


def diag_from_node(
        kind: str,
        message: str,
        *,
        module_name: Optional[str],
        filename: Optional[str],
        node: Optional[Node],
) -> Diagnostic:
    line = column = end_line = end_column = None
    if node is not None and node.span is not None:
        s = node.span
        line = s.start_line
        column = s.start_column
        end_line = s.end_line
        end_column = s.end_column
    return Diagnostic(
        kind=kind,
        message=message,
        module_name=module_name,
        filename=filename,
        line=line,
        column=column,
        end_line=end_line,
        end_column=end_column,
    )

def diag_from_token(
        kind: str,
        message: str,
        *,
        module_name: Optional[str],
        filename: Optional[str],
        token: Optional[Token],
) -> Diagnostic:
    line = column = end_line = end_column = None
    if token is not None:
        line = token.line
        column = token.column
    return Diagnostic(
        kind=kind,
        message=message,
        module_name=module_name,
        filename=filename,
        line=line,
        column=column,
        end_line=end_line,
        end_column=end_column,
    )
