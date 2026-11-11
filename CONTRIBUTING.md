# Contributing

Thanks for taking an interest. This is a small, deliberately plain tool and set of templates: standard library only, deterministic output, and documents that read as neutral practitioner guidance. Changes should keep it that way.

## Ground rules

1. **No real data, ever.** Do not commit material from a real organisation, person, supplier or incident. The example is fictional, and any new example should use invented names.
2. **Standard library only** for the `day_planner` package. Test tooling is fine under the `dev` extra.
3. **Deterministic output.** The same inputs must give byte-identical files. Sort anything whose order matters, never read the clock or the network, and never write timestamps into outputs.
4. **Every placement needs a reason.** If a change moves, drops or adds a block, the output should say why in plain English, and `docs/how-the-planner-works.md` should describe the rule.
5. **Suggestions, not standards.** The operating rhythm is generic practitioner guidance. Do not state that a law, regulation or standard requires a frequency unless you have checked the primary source and say so in the change.
6. **Vendor-neutral.** Say "service desk" or "ticketing system", not a product name.
7. **British English, plain tone, no long dashes.** A test fails if an em dash or en dash appears in any text file. Use commas, colons, full stops or brackets.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

## Changing behaviour

The files under `examples/output/` are compared with a fresh run by the tests, so a behaviour change needs them regenerated in the same change:

```bash
python scripts/regenerate_examples.py
python scripts/build_rhythm_doc.py      # after editing data/operating-rhythm.json
python -m pytest -q
```

If figures in the README or the docs change, update them from the new output. Every figure in the documentation must come from a real run.

The screenshot is made with Playwright, which is not a dependency of the tool:

```bash
python scripts/make_screenshot.py
```

The diagrams are Mermaid sources in `docs/images/`. Render them with the Mermaid CLI and commit both files:

```bash
mmdc -i docs/images/day-flow.mmd -o docs/images/day-flow.svg -b white
mmdc -i docs/images/placement.mmd -o docs/images/placement.svg -b white
```

## Changing the operating rhythm

Edit `data/operating-rhythm.json`, then run `python scripts/build_rhythm_doc.py`. Keep items specific, give a typical time in minutes and a one-line reason. Keep the note that these are suggestions.

## Pull request checklist

- [ ] Tests added or updated and passing
- [ ] Example outputs regenerated if behaviour changed
- [ ] Documentation figures updated from real output
- [ ] No real names, data or credentials in the diff
- [ ] No long dashes, no product names

## Reporting concerns

The tool reads local files and makes no network calls. If you find a way for crafted input to cause harm, please open a private security advisory on the repository rather than a public issue.
