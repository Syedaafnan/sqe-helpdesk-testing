"""Unit tests for the test-data generator (GEN-xx).

The generator decides which values the API tests send and whether each one
must be accepted, so a fault here silently weakens the whole API suite. These
tests pin its output exactly; the generator is also the second mutation target.
"""

import json

import pytest

from tests.team.datagen import generate as g

pytestmark = pytest.mark.unit


def by_partition(cases):
    return {c["partition"]: c for c in cases}


# ------------------------------------------------------------------ helpers
@pytest.mark.parametrize("n", [1, 2, 49, 50, 51, 150, 200, 201])
def test_gen01_text_of_length_exact_and_trimmed(n):
    s = g.text_of_length(n)
    assert len(s) == n
    assert s == s.strip()


def test_gen02_text_of_length_zero_and_negative():
    assert g.text_of_length(0) == ""
    assert g.text_of_length(-3) == ""


def test_gen03_text_of_length_is_deterministic_prefix():
    assert g.text_of_length(9) == "Generated"
    assert g.text_of_length(10) == "Generatedx"  # trailing space replaced


@pytest.mark.parametrize("n", [13, 50, 254, 255])
def test_gen04_email_of_length(n):
    e = g.email_of_length(n)
    assert len(e) == n
    assert e.endswith("@example.com")
    assert set(e[: n - 12]) == {"u"}


def test_gen05_case_record_shape():
    c = g.case("op", "S", "f", "BVA", "max", 5, True)
    assert c == {
        "id": "op.f.BVA.max", "operation": "op", "schema": "S", "field": "f",
        "technique": "BVA", "partition": "max", "value": 5, "omit": False, "valid": True,
    }
    assert g.case("op", "S", "f", "EP", "missing", None, False, omit=True)["omit"] is True


# ---------------------------------------------------------------- integers
def test_gen06_integer_range_ep_and_bva():
    cases = by_partition(g.integer_cases("op", "S", "priority", {"type": "integer", "minimum": 1, "maximum": 5}))
    expected = {
        "valid_in_range": (3, True), "wrong_type": ("abc", False), "fraction": (2.5, False),
        "below_range": (-9, False), "above_range": (15, False),
        "min-1": (0, False), "min": (1, True), "min+1": (2, True),
        "max-1": (4, True), "max": (5, True), "max+1": (6, False),
    }
    assert {k: (v["value"], v["valid"]) for k, v in cases.items()} == expected
    assert all(cases[k]["technique"] == "BVA" for k in ("min-1", "min", "min+1", "max-1", "max", "max+1"))
    assert all(cases[k]["technique"] == "EP" for k in ("valid_in_range", "wrong_type", "fraction"))


def test_gen07_integer_only_minimum():
    cases = by_partition(g.integer_cases("op", "S", "n", {"type": "integer", "minimum": 4}))
    assert cases["valid_in_range"]["value"] == 4
    assert "above_range" not in cases and "max" not in cases
    assert (cases["min-1"]["valid"], cases["min"]["valid"], cases["min+1"]["valid"]) == (False, True, True)


def test_gen08_integer_only_maximum():
    cases = by_partition(g.integer_cases("op", "S", "n", {"type": "integer", "maximum": 7}))
    assert cases["valid_in_range"]["value"] == 7
    assert "below_range" not in cases and "min" not in cases
    assert (cases["max-1"]["valid"], cases["max"]["valid"], cases["max+1"]["valid"]) == (True, True, False)


def test_gen09_integer_unbounded():
    cases = by_partition(g.integer_cases("op", "S", "n", {"type": "integer"}))
    assert set(cases) == {"valid_in_range", "wrong_type", "fraction"}
    assert cases["valid_in_range"]["value"] == 0


def test_gen10_integer_enum():
    cases = by_partition(g.integer_cases("op", "S", "status", {"type": "integer", "enum": [3, 1, 2]}))
    assert [cases[f"enum_{v}"]["valid"] for v in (1, 2, 3)] == [True, True, True]
    got = {k: (cases[k]["value"], cases[k]["valid"]) for k in ("min-1", "min", "min+1", "max-1", "max", "max+1")}
    assert got == {"min-1": (0, False), "min": (1, True), "min+1": (2, True),
                   "max-1": (2, True), "max": (3, True), "max+1": (4, False)}
    assert cases["wrong_type"]["valid"] is False
    assert "fraction" not in cases


def test_gen11_integer_enum_with_gap_uses_membership():
    cases = by_partition(g.integer_cases("op", "S", "s", {"type": "integer", "enum": [1, 3]}))
    assert cases["min+1"]["value"] == 2 and cases["min+1"]["valid"] is False


def test_gen12_integer_reference():
    cases = g.integer_cases("op", "S", "queue", {"type": "integer", "minimum": 1, "x-reference": "Queue"})
    assert [(c["partition"], c["value"], c["valid"]) for c in cases] == [
        ("existing_reference", "{ref}", True),
        ("unknown_reference", 999999, False),
        ("wrong_type", "abc", False),
        ("min-1", 0, False),
    ]
    no_min = g.integer_cases("op", "S", "queue", {"type": "integer", "x-reference": "Queue"})
    assert len(no_min) == 3


# ----------------------------------------------------------------- strings
def test_gen13_string_length_bva():
    cases = by_partition(g.string_cases("op", "S", "title", {"type": "string", "minLength": 1, "maxLength": 200, "example": "Ex"}))
    assert cases["valid_text"]["value"] == "Ex" and cases["valid_text"]["valid"] is True
    assert cases["wrong_type"]["value"] == ["not", "a", "string"]
    got = {k: (len(cases[k]["value"]), cases[k]["valid"]) for k in
           ("minLength-1", "minLength", "minLength+1", "maxLength-1", "maxLength", "maxLength+1")}
    assert got == {"minLength-1": (0, False), "minLength": (1, True), "minLength+1": (2, True),
                   "maxLength-1": (199, True), "maxLength": (200, True), "maxLength+1": (201, False)}


def test_gen14_string_default_example_and_negative_length_skipped():
    cases = by_partition(g.string_cases("op", "S", "c", {"type": "string", "minLength": 0}))
    assert cases["valid_text"]["value"] == "Text"
    assert "minLength-1" not in cases
    assert cases["minLength"]["value"] == "" and cases["minLength"]["valid"] is True
    assert len(cases["minLength+1"]["value"]) == 1


def test_gen15_email_cases():
    cases = by_partition(g.string_cases("op", "S", "e", {"type": "string", "format": "email", "maxLength": 254}))
    assert (cases["valid_email"]["value"], cases["valid_email"]["valid"]) == ("sam.rivera@example.com", True)
    assert (cases["missing_at_sign"]["value"], cases["missing_at_sign"]["valid"]) == ("sam.rivera.example.com", False)
    assert (cases["missing_domain"]["value"], cases["missing_domain"]["valid"]) == ("sam.rivera@", False)
    assert "valid_text" not in cases
    assert cases["maxLength"]["value"].endswith("@example.com") and len(cases["maxLength+1"]["value"]) == 255
    assert cases["maxLength+1"]["valid"] is False


def test_gen16_short_email_min_length_uses_empty_string():
    cases = by_partition(g.string_cases("op", "S", "e", {"type": "string", "format": "email", "minLength": 13}))
    assert cases["minLength-1"]["value"] == ""
    assert len(cases["minLength"]["value"]) == 13 and "@" in cases["minLength"]["value"]


def test_gen17_boolean_cases():
    assert [(c["value"], c["valid"]) for c in g.boolean_cases("op", "S", "b", {})] == [
        (True, True), (False, True), ("maybe", False)]


# -------------------------------------------------------------- whole spec
SPEC = {
    "paths": {
        "/t/": {
            "get": {"operationId": "list"},
            "post": {
                "operationId": "create",
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/T"}}}},
            },
        },
        "/t/{id}/": {"patch": {"operationId": "noBody"}, "delete": {"operationId": "del"}},
    },
    "components": {"schemas": {"T": {
        "type": "object", "required": ["name"],
        "properties": {
            "name": {"type": "string", "maxLength": 3},
            "flag": {"type": "boolean"},
        },
    }}},
}


def test_gen18_resolve_and_operations():
    assert g.resolve(SPEC, "#/components/schemas/T")["required"] == ["name"]
    assert list(g.operations(SPEC)) == [("create", "POST", "/t/", "#/components/schemas/T")]


def test_gen19_generate_required_and_optional():
    cases = g.generate(SPEC)
    ids = [c["id"] for c in cases]
    assert "create.name.EP.missing_required" in ids and "create.name.EP.null" in ids
    assert "create.flag.EP.omitted_optional" in ids and "create.flag.EP.null" not in ids
    m = {c["id"]: c for c in cases}
    assert m["create.name.EP.missing_required"]["omit"] is True and m["create.name.EP.missing_required"]["valid"] is False
    assert m["create.name.EP.null"]["omit"] is False and m["create.name.EP.null"]["value"] is None
    assert m["create.name.EP.null"]["valid"] is False  # kills generate_69 (run 2)
    assert m["create.flag.EP.omitted_optional"]["valid"] is True and m["create.flag.EP.omitted_optional"]["omit"] is True
    assert all(c["schema"] == "T" for c in cases)
    assert len(cases) == 5 + 2 + 3 + 1  # name: 2 EP + 3 BVA, required x2, flag x3, optional


def test_gen20_generate_rejects_duplicate_ids(monkeypatch):
    monkeypatch.setitem(g.GENERATORS, "boolean", lambda op, s, f, p: [g.case(op, s, f, "EP", "x", 1, True)] * 2)
    with pytest.raises(ValueError, match="duplicate case ids"):
        g.generate(SPEC)


def test_gen21_summary_counts():
    rows = g.summary(g.generate(SPEC))
    assert rows[("create", "name")] == {"EP": 4, "BVA": 3, "valid": 3, "invalid": 4}
    assert rows[("create", "flag")] == {"EP": 4, "BVA": 0, "valid": 3, "invalid": 1}


# -------------------------------------------------------------------- diff
def test_gen22_diff_added_removed_changed_unchanged():
    old = [g.case("o", "S", "a", "EP", "p", 1, True), g.case("o", "S", "b", "EP", "p", 2, True),
           g.case("o", "S", "c", "EP", "p", 3, True)]
    new = [g.case("o", "S", "a", "EP", "p", 1, True), g.case("o", "S", "c", "EP", "p", 3, False),
           g.case("o", "S", "d", "EP", "p", "x" * 40, False)]
    assert g.diff(old, new) == [
        "- removed  o.b.EP.p",
        "~ changed  o.c.EP.p: value 3 -> 3, valid True -> False",
        "+ added    o.d.EP.p: value=<string len 40> valid=False",
    ]
    assert g.diff(old, old) == []


def test_gen23_short():
    assert g._short(5) == "5"
    assert g._short("a" * 28) == '"' + "a" * 28 + '"'  # 30 chars, kept
    assert g._short("a" * 29) == "<string len 29>"


# -------------------------------------------------------------------- CLI
def test_gen24_main_writes_cases_and_prints_summary(tmp_path, capsys):
    spec = tmp_path / "s.yaml"
    spec.write_text(json.dumps(SPEC))  # JSON is valid YAML
    out = tmp_path / "sub" / "cases.json"
    assert g.main(["--spec", str(spec), "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["spec"] == "s.yaml" and data["count"] == 11 and len(data["cases"]) == 11
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == f"11 cases written to {out}"
    assert printed[1].split() == ["operation", "field", "EP", "BVA", "valid", "invalid"]
    assert printed[2].split() == ["create", "name", "4", "3", "3", "4"]


def test_gen25_main_diff_mode(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps({"cases": [g.case("o", "S", "a", "EP", "p", 1, True)]}))
    b.write_text(json.dumps({"cases": [g.case("o", "S", "a", "EP", "p", 2, True)]}))
    assert g.main(["--diff", str(a), str(b)]) == 0
    assert capsys.readouterr().out == "~ changed  o.a.EP.p: value 1 -> 2, valid True -> True\n"
    assert g.main(["--diff", str(a), str(a)]) == 0
    assert capsys.readouterr().out == "no differences\n"


def test_gen26_default_paths():
    assert g.DEFAULT_SPEC.name == "openapi.yaml"
    assert g.DEFAULT_OUT.parts[-2:] == ("generated", "cases.json")


# ---------------------------------------------- added after mutation analysis
# GEN27-GEN33 kill the killable survivors listed in docs/team/MUTATION.md.
INT_RANGE = {"type": "integer", "minimum": 1, "maximum": 5}
GENERATOR_INPUTS = [
    (g.integer_cases, {"type": "integer", "minimum": 1, "x-reference": "Queue"}),
    (g.integer_cases, {"type": "integer", "enum": [1, 2]}),
    (g.integer_cases, INT_RANGE),
    (g.string_cases, {"type": "string", "minLength": 1, "maxLength": 3}),
    (g.string_cases, {"type": "string", "format": "email", "minLength": 13, "maxLength": 20}),
    (g.boolean_cases, {"type": "boolean"}),
]
BVA_PARTITIONS = {"min-1", "min", "min+1", "max-1", "max", "max+1",
                  "minLength-1", "minLength", "minLength+1", "maxLength-1", "maxLength", "maxLength+1"}


@pytest.mark.parametrize("gen, prop", GENERATOR_INPUTS)
def test_gen27_every_record_carries_its_operation_schema_field_and_technique(gen, prop):
    """Kills ~100 survivors that swapped op/schema/field/technique for None,
    'XXEPXX' or 'ep': the API tests route each case by these fields."""
    for c in gen("createX", "XSchema", "fld", prop):
        assert (c["operation"], c["schema"], c["field"]) == ("createX", "XSchema", "fld")
        assert c["technique"] == ("BVA" if c["partition"] in BVA_PARTITIONS else "EP")
        assert c["id"] == f"createX.fld.{c['technique']}.{c['partition']}"
        assert c["valid"] in (True, False) and isinstance(c["valid"], bool)


def test_gen28_exact_invalid_values_and_partitions():
    """Kills wrong_type value swaps ('abc' -> None / 'ABC'), enum value -> None
    and the boolean partition renames."""
    ints = by_partition(g.integer_cases("o", "S", "f", {"type": "integer", "enum": [1, 2]}))
    assert ints["wrong_type"]["value"] == "abc" and ints["enum_1"]["value"] == 1 and ints["enum_2"]["value"] == 2
    assert [c["partition"] for c in g.boolean_cases("o", "S", "f", {})] == ["true", "false", "wrong_type"]


def test_gen29_valid_in_range_is_an_integer():
    """Kills mutant `(lo + hi) / 2`: 3.0 == 3 in Python but serialises as 3.0,
    which the API would receive as a fraction (an invalid value) in a 'valid' case."""
    mid = by_partition(g.integer_cases("o", "S", "f", INT_RANGE))["valid_in_range"]["value"]
    assert type(mid) is int and json.dumps(mid) == "3"


SPEC_PUT_PATCH = {
    "paths": {"/a/{id}/": {
        "put": {"operationId": "replaceA", "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/A"}}}}},
        "patch": {"operationId": "updateA", "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/A"}}}}},
    }},
    "components": {"schemas": {"A": {"type": "object", "properties": {"b": {"type": "boolean"}}}}},
}


def test_gen30_put_and_patch_operations_and_schema_without_required():
    """Kills the 'put'/'patch' literal mutants and `schema.get('required', None)`."""
    assert [o[:2] for o in g.operations(SPEC_PUT_PATCH)] == [("replaceA", "PUT"), ("updateA", "PATCH")]
    cases = g.generate(SPEC_PUT_PATCH)
    assert len(cases) == 8 and all(c["schema"] == "A" for c in cases)


def test_gen31_main_uses_default_paths(tmp_path, monkeypatch):
    """Kills `default=None` on --spec / --out."""
    spec = tmp_path / "default.yaml"
    spec.write_text(json.dumps(SPEC))
    monkeypatch.setattr(g, "DEFAULT_SPEC", spec)
    monkeypatch.setattr(g, "DEFAULT_OUT", tmp_path / "out.json")
    assert g.main([]) == 0
    assert json.loads((tmp_path / "out.json").read_text())["spec"] == "default.yaml"


def test_gen32_main_creates_nested_dirs_rewrites_and_indents(tmp_path):
    """Kills the mkdir(parents/exist_ok) and json indent mutants: the output
    file is reviewed in pull requests, so its layout is part of the contract."""
    spec = tmp_path / "s.yaml"
    spec.write_text(json.dumps(SPEC))
    out = tmp_path / "a" / "b" / "cases.json"
    assert g.main(["--spec", str(spec), "--out", str(out)]) == 0
    assert g.main(["--spec", str(spec), "--out", str(out)]) == 0  # directory already exists
    assert out.read_text().startswith('{\n  "spec": "s.yaml",\n  "count": 11,')


def test_gen33_main_diff_prints_one_line_per_change(tmp_path, capsys):
    """Kills the `"XX\nXX".join` mutant."""
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps({"cases": [g.case("o", "S", "a", "EP", "p", 1, True), g.case("o", "S", "b", "EP", "p", 1, True)]}))
    b.write_text(json.dumps({"cases": []}))
    g.main(["--diff", str(a), str(b)])
    assert capsys.readouterr().out == "- removed  o.a.EP.p\n- removed  o.b.EP.p\n"


def test_gen34_script_entry_point_exits_with_main_status(tmp_path, monkeypatch, capsys):
    """Runs generate.py as a script (python generate.py --diff A B), covering the
    __main__ guard that CI and the documentation use."""
    import runpy
    import sys

    a = tmp_path / "a.json"
    a.write_text(json.dumps({"cases": []}))
    monkeypatch.setattr(sys, "argv", ["generate.py", "--diff", str(a), str(a)])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(g.__file__, run_name="__main__")
    assert exit_info.value.code == 0
    assert capsys.readouterr().out == "no differences\n"
