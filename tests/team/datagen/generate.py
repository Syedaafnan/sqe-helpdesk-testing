"""Generate EP classes and 3-point BVA values from an OpenAPI spec.

Usage:
    python tests/team/datagen/generate.py                      # default spec -> generated/cases.json
    python tests/team/datagen/generate.py --spec other.yaml --out other.json
    python tests/team/datagen/generate.py --diff old.json new.json

For every property of every requestBody schema the generator derives:

* EP  - one valid representative, plus one invalid class per violated
        constraint (wrong type, missing required field, null, bad format,
        not in enum, unknown reference). One invalid value per case.
* BVA - 3-point boundary values around every limit:
        minimum/maximum        -> limit-1, limit, limit+1
        minLength/maxLength    -> length-1, length, length+1
        enum (integer)         -> min-1, min, min+1, max-1, max, max+1

Each case says whether the value is valid against the schema. The API tests
(tests/team/api/) load the output and assert 2xx for valid and 400 for
invalid values, so changing a constraint in the spec changes the tests.
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_SPEC = HERE / "openapi.yaml"
DEFAULT_OUT = HERE / "generated" / "cases.json"

TEXT = "Generated ticket text for boundary value analysis "


def text_of_length(n):
    """Deterministic printable string of exactly n characters (no edge spaces)."""
    if n <= 0:
        return ""
    s = (TEXT * (n // len(TEXT) + 1))[:n]
    return s[:-1] + "x" if s.endswith(" ") else s


def email_of_length(n):
    """A syntactically valid e-mail address of exactly n characters (n >= 13).

    Django's EmailValidator limits domain labels to 63 characters but does not
    limit the local part, so the extra length goes before the '@'.
    """
    domain = "@example.com"  # 12 characters
    return "u" * (n - len(domain)) + domain


def case(op, schema, field, technique, partition, value, valid, omit=False):
    return {
        "id": f"{op}.{field}.{technique}.{partition}",
        "operation": op,
        "schema": schema,
        "field": field,
        "technique": technique,
        "partition": partition,
        "value": value,
        "omit": omit,
        "valid": valid,
    }


def integer_cases(op, schema, field, prop):
    out = []
    if "x-reference" in prop:
        out.append(case(op, schema, field, "EP", "existing_reference", "{ref}", True))
        out.append(case(op, schema, field, "EP", "unknown_reference", 999999, False))
        out.append(case(op, schema, field, "EP", "wrong_type", "abc", False))
        lo = prop.get("minimum")
        if lo is not None:
            out.append(case(op, schema, field, "BVA", "min-1", lo - 1, False))
        return out

    if "enum" in prop:
        values = sorted(prop["enum"])
        for v in values:
            out.append(case(op, schema, field, "EP", f"enum_{v}", v, True))
        lo, hi = values[0], values[-1]
        out.append(case(op, schema, field, "EP", "wrong_type", "abc", False))
    else:
        lo, hi = prop.get("minimum"), prop.get("maximum")
        mid = (lo + hi) // 2 if lo is not None and hi is not None else (lo or hi or 0)
        out.append(case(op, schema, field, "EP", "valid_in_range", mid, True))
        out.append(case(op, schema, field, "EP", "wrong_type", "abc", False))
        out.append(case(op, schema, field, "EP", "fraction", 2.5, False))
        if lo is not None:
            out.append(case(op, schema, field, "EP", "below_range", lo - 10, False))
        if hi is not None:
            out.append(case(op, schema, field, "EP", "above_range", hi + 10, False))

    allowed = set(prop["enum"]) if "enum" in prop else None

    def ok(v):
        if allowed is not None:
            return v in allowed
        return (lo is None or v >= lo) and (hi is None or v <= hi)

    if lo is not None:
        for name, v in (("min-1", lo - 1), ("min", lo), ("min+1", lo + 1)):
            out.append(case(op, schema, field, "BVA", name, v, ok(v)))
    if hi is not None:
        for name, v in (("max-1", hi - 1), ("max", hi), ("max+1", hi + 1)):
            out.append(case(op, schema, field, "BVA", name, v, ok(v)))
    return out


def string_cases(op, schema, field, prop):
    out = []
    lo, hi = prop.get("minLength"), prop.get("maxLength")
    is_email = prop.get("format") == "email"
    make = email_of_length if is_email else text_of_length

    if is_email:
        out.append(case(op, schema, field, "EP", "valid_email", "sam.rivera@example.com", True))
        out.append(case(op, schema, field, "EP", "missing_at_sign", "sam.rivera.example.com", False))
        out.append(case(op, schema, field, "EP", "missing_domain", "sam.rivera@", False))
    else:
        out.append(case(op, schema, field, "EP", "valid_text", prop.get("example", "Text"), True))
    out.append(case(op, schema, field, "EP", "wrong_type", ["not", "a", "string"], False))

    if lo is not None:
        for name, n in (("minLength-1", lo - 1), ("minLength", lo), ("minLength+1", lo + 1)):
            if n < 0:
                continue
            value = make(n) if (not is_email or n >= 13) else ""
            out.append(case(op, schema, field, "BVA", name, value, n >= lo))
    if hi is not None:
        for name, n in (("maxLength-1", hi - 1), ("maxLength", hi), ("maxLength+1", hi + 1)):
            out.append(case(op, schema, field, "BVA", name, make(n), n <= hi))
    return out


def boolean_cases(op, schema, field, _prop):
    return [
        case(op, schema, field, "EP", "true", True, True),
        case(op, schema, field, "EP", "false", False, True),
        case(op, schema, field, "EP", "wrong_type", "maybe", False),
    ]


GENERATORS = {"integer": integer_cases, "string": string_cases, "boolean": boolean_cases}


def resolve(spec, ref):
    node = spec
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def operations(spec):
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method not in ("post", "put", "patch") or "requestBody" not in op:
                continue
            schema_ref = op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
            yield op["operationId"], method.upper(), path, schema_ref


def generate(spec):
    cases = []
    for op_id, _method, _path, ref in operations(spec):
        name = ref.rsplit("/", 1)[-1]
        schema = resolve(spec, ref)
        required = set(schema.get("required", []))
        for field, prop in schema["properties"].items():
            gen = GENERATORS[prop["type"]]
            cases.extend(gen(op_id, name, field, prop))
            if field in required:
                cases.append(case(op_id, name, field, "EP", "missing_required", None, False, omit=True))
                cases.append(case(op_id, name, field, "EP", "null", None, False))
            else:
                cases.append(case(op_id, name, field, "EP", "omitted_optional", None, True, omit=True))
    ids = [c["id"] for c in cases]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate case ids: {sorted(dupes)}")
    return cases


def summary(cases):
    rows = {}
    for c in cases:
        key = (c["operation"], c["field"])
        r = rows.setdefault(key, {"EP": 0, "BVA": 0, "valid": 0, "invalid": 0})
        r[c["technique"]] += 1
        r["valid" if c["valid"] else "invalid"] += 1
    return rows


def diff(old_cases, new_cases):
    old = {c["id"]: c for c in old_cases}
    new = {c["id"]: c for c in new_cases}
    lines = []
    for cid in sorted(set(old) | set(new)):
        o, n = old.get(cid), new.get(cid)
        if o is None:
            lines.append(f"+ added    {cid}: value={_short(n['value'])} valid={n['valid']}")
        elif n is None:
            lines.append(f"- removed  {cid}")
        elif (o["value"], o["valid"]) != (n["value"], n["valid"]):
            lines.append(
                f"~ changed  {cid}: value {_short(o['value'])} -> {_short(n['value'])}, "
                f"valid {o['valid']} -> {n['valid']}"
            )
    return lines


def _short(v):
    s = json.dumps(v)
    return s if len(s) <= 30 else f"<string len {len(v)}>"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--diff", nargs=2, type=Path, metavar=("OLD", "NEW"))
    args = p.parse_args(argv)

    if args.diff:
        old, new = (json.loads(f.read_text())["cases"] for f in args.diff)
        lines = diff(old, new)
        print("\n".join(lines) if lines else "no differences")
        return 0

    spec = yaml.safe_load(args.spec.read_text())
    cases = generate(spec)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"spec": args.spec.name, "count": len(cases), "cases": cases}, indent=2)
    )
    print(f"{len(cases)} cases written to {args.out}")
    print(f"{'operation':<16}{'field':<18}{'EP':>4}{'BVA':>5}{'valid':>7}{'invalid':>9}")
    for (op, field), r in summary(cases).items():
        print(f"{op:<16}{field:<18}{r['EP']:>4}{r['BVA']:>5}{r['valid']:>7}{r['invalid']:>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
