# SPDX-License-Identifier: MIT OR Apache-2.0
# Copyright (c) 2026 gwz
"""Tests for L0 LaTeX normalization."""

from pathlib import Path

from compiler.docgen.l0_docgen_latex import normalize_latex_site


def test_normalize_latex_site_adds_module_banner_without_symbol_note(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/shared/l0/stdlib/std/unit.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module std.unit;\n", encoding="utf-8")

    (xml_dir / "unit_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="unit_8l0" kind="file" language="C++">
    <compoundname>unit.l0</compoundname>
    <location file="compiler/shared/l0/stdlib/std/unit.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )
    (xml_dir / "struct_unit.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="struct_unit" kind="struct" language="C++">
    <compoundname>Unit</compoundname>
    <location file="compiler/shared/l0/stdlib/std/unit.l0" line="3" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "unit_8l0.tex").write_text(
        """\\doxysection{compiler/shared/l0/stdlib/std/unit.l0 File Reference}
\\hypertarget{unit_8l0}{}\\label{unit_8l0}\\index{compiler/shared/l0/stdlib/std/unit.l0@{compiler/shared/l0/stdlib/std/unit.l0}}
\\doxysubsubsection*{Functions}
""",
        encoding="utf-8",
    )
    (latex_dir / "struct_unit.tex").write_text(
        """\\doxysection{Unit Struct Reference}
\\hypertarget{struct_unit}{}\\label{struct_unit}\\index{Unit@{Unit}}
Definition of the Unit type.
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    file_page = (latex_dir / "unit_8l0.tex").read_text(encoding="utf-8")
    symbol_page = (latex_dir / "struct_unit.tex").read_text(encoding="utf-8")
    assert r"\textbf{Module:} \texttt{std.unit}\par\medskip" in file_page
    assert "Defined in module" not in symbol_page


def test_normalize_latex_site_does_not_inject_symbol_source_note(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/stage2_l0/src/sem_context.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module sem_context;\n", encoding="utf-8")

    (xml_dir / "sem__context_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="sem__context_8l0" kind="file" language="C++">
    <compoundname>sem_context.l0</compoundname>
    <location file="compiler/stage2_l0/src/sem_context.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )
    (xml_dir / "struct_analysis_result.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="struct_analysis_result" kind="struct" language="C++">
    <compoundname>AnalysisResult</compoundname>
    <location file="compiler/stage2_l0/src/sem_context.l0" line="5" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "struct_analysis_result.tex").write_text(
        """\\doxysection{AnalysisResult Struct Reference}
\\hypertarget{struct_analysis_result}{}\\label{struct_analysis_result}\\index{AnalysisResult@{AnalysisResult}}
Body.
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    symbol_page = (latex_dir / "struct_analysis_result.tex").read_text(encoding="utf-8")
    assert "Defined in module" not in symbol_page


def test_normalize_latex_site_normalizes_function_signature_spacing(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/stage2_l0/src/driver.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module driver;\n", encoding="utf-8")

    (xml_dir / "driver_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="driver_8l0" kind="file" language="C++">
    <compoundname>driver.l0</compoundname>
    <location file="compiler/stage2_l0/src/driver.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "driver_8l0.tex").write_text(
        """\\doxysection{compiler/stage2_l0/src/driver.l0 File Reference}
\\hypertarget{driver_8l0}{}\\label{driver_8l0}\\index{compiler/stage2_l0/src/driver.l0@{compiler/stage2_l0/src/driver.l0}}
func \\doxymbox{\\hyperlink{driver_8l0_a1}{dr\\+_vs\\+_has}} (items:\\+\\+Vector\\+String \\texorpdfstring{$\\ast$}{*}, module\\+_name:\\+string) -\\/$>$ bool
func driver\\+_find\\+_unit (\\begin{DoxyParamCaption}\\item[{self:\\+\\+Driver\\+State \\texorpdfstring{$\\ast$}{*}}]{}{, }\\item[{module\\+_name:\\+string}]{}{}\\end{DoxyParamCaption}) -\\/$>$ bool
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "driver_8l0.tex").read_text(encoding="utf-8")
    assert r"items: Vector\+String\texorpdfstring{$\ast$}{*}, module\+_name: string" in page
    assert r"self: Driver\+State\texorpdfstring{$\ast$}{*}" in page


def test_normalize_latex_site_normalizes_struct_member_signatures(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/stage2_l0/src/util/diag.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module util.diag;\n", encoding="utf-8")

    (xml_dir / "diag_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="diag_8l0" kind="file" language="C++">
    <compoundname>diag.l0</compoundname>
    <location file="compiler/stage2_l0/src/util/diag.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )
    (xml_dir / "struct_diagnostic.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="struct_diagnostic" kind="struct" language="C++">
    <compoundname>Diagnostic</compoundname>
    <location file="compiler/stage2_l0/src/util/diag.l0" line="5" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "struct_diagnostic.tex").write_text(
        """\\doxysection{Diagnostic Struct Reference}
\\hypertarget{struct_diagnostic}{}\\label{struct_diagnostic}\\index{Diagnostic@{Diagnostic}}
\\doxysubsubsection*{Public Attributes}
\\begin{DoxyCompactItemize}
\\item
string \\doxymbox{\\hyperlink{struct_diagnostic_a1}{phase}}
\\item
\\doxymbox{\\hyperlink{diag_8l0_a1}{Diagnostic\\+Severity}} \\doxymbox{\\hyperlink{struct_diagnostic_a2}{severity}}
\\end{DoxyCompactItemize}
\\doxysubsection{Detailed Description}
Body.
\\label{doc-variable-members}
\\Hypertarget{struct_diagnostic_doc-variable-members}
\\doxysubsection{Member Data Documentation}
{\\footnotesize\\ttfamily \\label{struct_diagnostic_a1}
string Diagnostic::\\+phase}
{\\footnotesize\\ttfamily \\label{struct_diagnostic_a2}
\\doxymbox{\\hyperlink{diag_8l0_a1}{Diagnostic\\+Severity}} Diagnostic::\\+severity}
The documentation for this struct was generated from the following file:
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "struct_diagnostic.tex").read_text(encoding="utf-8")
    assert r"\doxymbox{\hyperlink{struct_diagnostic_a1}{phase}}: string" in page
    assert r"phase: string}" in page
    assert r"Diagnostic::\+phase" not in page


def test_normalize_latex_site_expands_l0_signature_link_text(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/shared/l0/stdlib/sys/rt.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module std.rt;\n", encoding="utf-8")

    (xml_dir / "rt_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="rt_8l0" kind="file" language="C++">
    <compoundname>rt.l0</compoundname>
    <location file="compiler/shared/l0/stdlib/sys/rt.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "l0__runtime_8h.tex").write_text(
        r"""\doxysection{l0_runtime.h File Reference}
\hypertarget{l0__runtime_8h}{}\label{l0__runtime_8h}\index{l0\_runtime.h@{l0\_runtime.h}}
L0 signature:\+ {\ttfamily extern func \doxylink{rt_8l0_a1}{rt\+\_\+string\+\_\+slice(s:\+ string, start:\+ int, end:\+ int)} \texorpdfstring{$\rightarrow$}{->} string;}
L0 signature:\+ {\ttfamily extern func \doxylink{unsafe_8l0_a2}{rt\+\_\+free}(ptr:\+ void\texorpdfstring{$\ast$}{*}?) \texorpdfstring{$\rightarrow$}{->} void;}
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "l0__runtime_8h.tex").read_text(encoding="utf-8")
    assert r"extern \doxylink{rt_8l0_a1}{func rt\+\_\+string\+\_\+slice(s:\+ string, start:\+ int, end:\+ int) \texorpdfstring{$\rightarrow$}{->} string};" in page
    assert r"extern \doxylink{unsafe_8l0_a2}{func rt\+\_\+free(ptr:\+ void\texorpdfstring{$\ast$}{*}?) \texorpdfstring{$\rightarrow$}{->} void};" in page


def test_normalize_latex_site_moves_extern_suffix_into_l0_signature_prefix(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/shared/l0/stdlib/sys/rt.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module std.rt;\n", encoding="utf-8")

    (xml_dir / "rt_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="rt_8l0" kind="file" language="C++">
    <compoundname>rt.l0</compoundname>
    <location file="compiler/shared/l0/stdlib/sys/rt.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "rt_8l0.tex").write_text(
        r"""\doxysection{rt.l0 File Reference}
\hypertarget{rt_8l0}{}\label{rt_8l0}\index{rt.l0@{rt.l0}}
{\footnotesize\ttfamily \label{rt_8l0_a1}
func rt\+\_\+string\+\_\+slice (\begin{DoxyParamCaption}\item[{s: string}]{}{, }\item[{start: int}]{}{, }\item[{end: int}]{}{}\end{DoxyParamCaption}) \texorpdfstring{$\rightarrow$}{->}  string\hspace{0.3cm}{\ttfamily [extern]}}
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "rt_8l0.tex").read_text(encoding="utf-8")
    assert r"extern func rt\+\_\+string\+\_\+slice (" in page
    assert r"\hspace{0.3cm}{\ttfamily [extern]}" not in page


def test_normalize_latex_site_normalizes_pointer_members_in_public_attributes(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/shared/l0/stdlib/std/hashmap.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module std.hashmap;\n", encoding="utf-8")

    (xml_dir / "hashmap_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="hashmap_8l0" kind="file" language="C++">
    <compoundname>hashmap.l0</compoundname>
    <location file="compiler/shared/l0/stdlib/std/hashmap.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )
    (xml_dir / "struct_string_ptr_map.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="struct_string_ptr_map" kind="struct" language="C++">
    <compoundname>StringPtrMap</compoundname>
    <location file="compiler/shared/l0/stdlib/std/hashmap.l0" line="5" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "struct_string_ptr_map.tex").write_text(
        """\\doxysection{StringPtrMap Struct Reference}
\\hypertarget{struct_string_ptr_map}{}\\label{struct_string_ptr_map}\\index{StringPtrMap@{StringPtrMap}}
\\doxysubsubsection*{Public Attributes}
\\begin{DoxyCompactItemize}
\\item
\\doxymbox{\\hyperlink{struct_array_base}{Array\\+Base}} \\texorpdfstring{$\\ast$}{*} \\doxymbox{\\hyperlink{struct_string_ptr_map_a1}{states}}
\\end{DoxyCompactItemize}
\\doxysubsection{Detailed Description}
Body.
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "struct_string_ptr_map.tex").read_text(encoding="utf-8")
    assert (
        r"\doxymbox{\hyperlink{struct_string_ptr_map_a1}{states}}: "
        r"\doxymbox{\hyperlink{struct_array_base}{Array\+Base}}\texorpdfstring{$\ast$}{*}"
    ) in page


def test_normalize_latex_site_injects_payload_enum_variants(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/stage2_l0/src/tokens.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        """module tokens;
enum TokenType {
    TT_EOF;
    TT_IDENT(text: string);
    TT_INT(text: string, value: int);
}
""",
        encoding="utf-8",
    )

    (xml_dir / "tokens_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="tokens_8l0" kind="file" language="C++">
    <compoundname>tokens.l0</compoundname>
    <sectiondef kind="enum">
      <memberdef kind="enum" id="tokens_8l0_1a" prot="public" static="no" strong="no">
        <type></type>
        <name>TokenType</name>
        <enumvalue id="tokens_8l0_1a1" prot="public"><name>TT_EOF</name></enumvalue>
        <briefdescription><para>Defines the TokenType enumeration.</para></briefdescription>
        <location file="compiler/stage2_l0/src/tokens.l0" line="2" bodystart="2" bodyend="6" />
      </memberdef>
    </sectiondef>
    <location file="compiler/stage2_l0/src/tokens.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "tokens_8l0.tex").write_text(
        """\\doxysection{compiler/stage2_l0/src/tokens.l0 File Reference}
\\hypertarget{tokens_8l0}{}\\label{tokens_8l0}\\index{compiler/stage2_l0/src/tokens.l0@{compiler/stage2_l0/src/tokens.l0}}
\\doxysubsubsection{\\texorpdfstring{TokenType}{TokenType}}
Description.
\\begin{DoxyEnumFields}[2]{Enumerator}
\\item TT\\+_EOF
\\end{DoxyEnumFields}
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "tokens_8l0.tex").read_text(encoding="utf-8")
    assert r"\textbf{Variants:}\\" in page
    assert r"\texttt{TT\_IDENT(text: string)}" in page
    assert r"\texttt{TT\_INT(text: string, value: int)}" in page
    assert r"\begin{DoxyEnumFields}" not in page


def test_normalize_latex_site_retargets_l0_links_away_from_python_symbols(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/stage2_l0/src/types.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module types;\n", encoding="utf-8")

    (xml_dir / "types_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="types_8l0" kind="file" language="C++">
    <compoundname>types.l0</compoundname>
    <location file="compiler/stage2_l0/src/types.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )
    (xml_dir / "struct_type.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="struct_type" kind="struct" language="C++">
    <compoundname>Type</compoundname>
    <location file="compiler/stage2_l0/src/types.l0" line="3" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "types_8l0.tex").write_text(
        """\\doxysection{compiler/stage2_l0/src/types.l0 File Reference}
\\hypertarget{types_8l0}{}\\label{types_8l0}\\index{compiler/stage2_l0/src/types.l0@{compiler/stage2_l0/src/types.l0}}
See \\doxylink{classl0__types_1_1_type}{Type} for details.
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "types_8l0.tex").read_text(encoding="utf-8")
    assert r"\doxylink{struct_type}{Type}" in page
    assert r"\doxylink{classl0__types_1_1_type}{Type}" not in page


def test_normalize_latex_site_uses_arrow_symbol_in_prose_only(tmp_path: Path, monkeypatch) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()
    source_path = tmp_path / "compiler/stage2_l0/src/demo.l0"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("module demo;\n", encoding="utf-8")

    (xml_dir / "demo_8l0.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="demo_8l0" kind="file" language="C++">
    <compoundname>demo.l0</compoundname>
    <location file="compiler/stage2_l0/src/demo.l0" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )

    (latex_dir / "demo_8l0.tex").write_text(
        """\\doxysection{compiler/stage2_l0/src/demo.l0 File Reference}
\\hypertarget{demo_8l0}{}\\label{demo_8l0}\\index{compiler/stage2_l0/src/demo.l0@{compiler/stage2_l0/src/demo.l0}}
Examples: Foo -\\/\\texorpdfstring{$>$}{>} Bar
func demo (x: int) -\\/$>$ bool
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "demo_8l0.tex").read_text(encoding="utf-8")
    assert r"Examples: Foo \texorpdfstring{$\rightarrow$}{->} Bar" in page
    assert r"func demo (x: int) \texorpdfstring{$\rightarrow$}{->} bool" in page


def test_normalize_latex_site_normalizes_prose_arrows_on_non_l0_pages(tmp_path: Path) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()

    (xml_dir / "demo_8py.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="demo_8py" kind="file" language="Python">
    <compoundname>demo.py</compoundname>
    <location file="compiler/stage1_py/demo.py" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )
    (latex_dir / "demo_8py.tex").write_text(
        """\\doxysection{demo.py File Reference}
\\hypertarget{demo_8py}{}\\label{demo_8py}\\index{demo.py@{demo.py}}
Examples: Foo -\\/\\texorpdfstring{$>$}{>} Bar
""",
        encoding="utf-8",
    )

    normalize_latex_site(xml_dir, latex_dir)

    page = (latex_dir / "demo_8py.tex").read_text(encoding="utf-8")
    assert r"Examples: Foo \texorpdfstring{$\rightarrow$}{->} Bar" in page


def test_normalize_latex_site_leaves_non_l0_pages_unchanged(tmp_path: Path) -> None:
    xml_dir = tmp_path / "xml"
    xml_dir.mkdir()
    latex_dir = tmp_path / "latex"
    latex_dir.mkdir()

    (xml_dir / "demo_8py.xml").write_text(
        """<?xml version='1.0' encoding='UTF-8' standalone='no'?>
<doxygen>
  <compounddef id="demo_8py" kind="file" language="Python">
    <compoundname>demo.py</compoundname>
    <location file="compiler/stage1_py/demo.py" line="1" />
  </compounddef>
</doxygen>
""",
        encoding="utf-8",
    )
    original = """\\doxysection{demo.py File Reference}
\\hypertarget{demo_8py}{}\\label{demo_8py}\\index{demo.py@{demo.py}}
"""
    (latex_dir / "demo_8py.tex").write_text(original, encoding="utf-8")

    normalize_latex_site(xml_dir, latex_dir)

    assert (latex_dir / "demo_8py.tex").read_text(encoding="utf-8") == original
