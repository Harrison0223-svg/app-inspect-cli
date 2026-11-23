# Contributing

Keep each topic branch focused. Include a reproducible synthetic fixture, expected and actual results, and exact test commands. Do not include private data, secrets, or unlicensed assets. Add a regression test for changes in behavior. Disclose material AI assistance and review the diff yourself before submitting.

## Offline checks

Use Python 3.9 or later. Preserve the standard-library-only runtime.

    python -m unittest discover -s tests -v
    python -m app_inspect --help

Use the fake Apple data in the test suite; regression tests should not require live requests.

## New contributors

For a first patch, choose an open issue labeled `good first issue`. Start with
the file and test command in that issue. Keep tests offline by using
`tests/fakeapple.py` or mocking the HTTP boundary rather than calling Apple.

Run the full unit suite before opening a PR. CI also checks the installed CLI,
MCP over stdio, and the composite GitHub Action. The composite-action smoke
test contacts the public App Store; an offline local pass does not validate it.
