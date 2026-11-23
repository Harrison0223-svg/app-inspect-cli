# Contributing

Keep each topic branch focused. Include a reproducible synthetic fixture, expected and actual results, and exact test commands. Do not include private data, secrets, or unlicensed assets. Add a regression test for changes in behavior. Disclose material AI assistance and review the diff yourself before submitting.

## Offline checks

Use Python 3.9 or later. Preserve the standard-library-only runtime.

    python -m unittest discover -s tests -v
    python -m app_inspect --help

Use the fake Apple data in the test suite; regression tests should not require live requests.
