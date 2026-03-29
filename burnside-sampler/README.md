# Burnside Sampler on the Symmetric Group

This is an interactive browser visualizer and verified prime-field implementation of the Burnside sampling process on the symmetric group, which arises from the finite-field flag variety in Type A as explained in the paper [Markov chains on Weyl groups from the geometry of the flag variety](https://arxiv.org/abs/2510.02285).

The project has two core layers:

- `web/`: a no-backend browser app that runs the sampler locally through Pyodide
- `burnside_sampler/`: the pure-Python implementation of the actual sampling algorithm, together with a Sage version used for correctness checks

The mathematical source of truth is still the original Sage notebook, which implements exactly the algorithm described in Section 3 of our paper.

- `sampling/sampling_burnside.ipynb`

## What This Repo Contains

- `burnside_sampler/pure_python.py`
  Prime-field Burnside sampler used in the browser app.
- `burnside_sampler/oracle_sage.py`
  Sage-backed reference extracted from the notebook for tests.
- `tests/`
  Correctness tests.
- `web/`
  Web app wrapper for the sampler.
- `run_tests.sh`
  Runs the Python tests and the Sage-backed verification suite.
- `serve_web.sh`
  Serves the repository locally for browser use.

## Browser App

To run it locally:

```sh
./serve_web.sh
```

Then open:

```txt
http://localhost:8000/web/index.html
```

For GitHub Pages, the repository root also includes a small redirecting `index.html`, so the project site can open directly from the repository URL.

The browser UI:

- simulates the Burnside chain locally
- restricts `q` to primes
- colors histogram bars by right Steinberg cell via the RSK insertion tableau `P`
- uses the mathematical kernel in Python for the actual sampling

## Verification

Run the full verification suite with:

```sh
./run_tests.sh
```

This checks:

- pure-Python finite-field linear algebra and Green-polynomial logic
- quotient and Springer-fiber sampling behavior
- alignment against Sage for the trusted oracle
- RSK / right-cell metadata used by the visualization

## Notes

- Sage is needed only for oracle verification, not for running the public web app!
