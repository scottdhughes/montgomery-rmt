# Spectral Bridge

This repository contains a reproducible finite-block Montgomery--RMT
comparison for zeta-zero spacing statistics, together with Lean 4 certificate
files for the finite bookkeeping used by the computation.

The paper-facing claim is deliberately finite:

> In the tested finite estimator grid, the two high Odlyzko blocks have smaller
> discrete RMS residuals from the GUE sine-kernel reference than the initial
> zeta-zero block, with GUE/GOE/Poisson controls included for scale.

This is not a proof of the Riemann hypothesis, Montgomery pair correlation, a
GUE limit theorem, or a physical Hamiltonian model.

## Contents

- `projects/montgomery-rmt/paper/`: TeX source and figure files for the note.
- `projects/montgomery-rmt/scripts/`: scripts used to rebuild the finite
  numerical comparisons, source package, and Lean-readable certificates.
- `projects/montgomery-rmt/data/`: finite input and processed data used by the
  release artifact.
- `projects/montgomery-rmt/outputs/`: finite metrics and paper figures.
- `lean/SpectralBridge/MontgomeryRMT/`: Mathlib-only Lean formalization and
  generated finite certificate data.
- `projects/montgomery-rmt/certificates/`: certificate provenance manifest.

## Reproduce

Install Python dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-rigorous.txt
```

Install Lean 4 with `elan`; this repository pins Lean and Mathlib through
`lean-toolchain`, `lakefile.toml`, and `lake-manifest.json`.

Run the full release check:

```bash
./build.sh
```

The build script:

1. regenerates the finite low/high comparison from the checked-in data,
2. regenerates the sensitivity metrics and paper figures,
3. exports generated Lean certificate data,
4. exports optional Arb-backed interval residual certificates when
   `python-flint` is installed,
5. builds the Lean project with `lake build`,
6. builds and audits the preprint source package.

For a first Lean-only check:

```bash
lake exe cache get
lake build
```

## Main finite values

The default discrete RMS residual chain is

```text
initial block: 0.0479815015085
10^12 block:  0.0399492422825
10^21 block:  0.0369651551678
```

The full finite sensitivity grid records:

```text
high blocks beat the initial block: 27/27 configurations
strict three-block monotonicity:    18/27 configurations
GUE beats Poisson controls:         156/162 comparisons
```

## Formal certificate boundary

The Lean layer certifies finite combinatorial and bookkeeping claims:

- finite block and adjacent-gap scaffolding;
- pair-sum index bounds;
- histogram count facts;
- accepted-pair count bounds;
- generated residual-score ordering over encoded finite data;
- generated Boolean-vector sensitivity summaries;
- Arb-backed interval residual ordering for the default zeta chain, when the
  interval certificate files are present.

The Lean layer does not certify:

- that the Odlyzko ordinates are zeta zeros;
- raw floating-point arithmetic;
- the Riemann hypothesis;
- Montgomery pair correlation;
- asymptotic GUE limits;
- physics claims.

## Paper

The TeX source package can be rebuilt with:

```bash
python projects/montgomery-rmt/scripts/build_preprint_package.py
python projects/montgomery-rmt/scripts/audit_paper_package.py \
  --package-dir projects/montgomery-rmt/dist/preprint_package
```

The paper source is intentionally written as a finite numerical note. It uses
public-facing block labels in text and figures.

## Citation

Use the metadata in `CITATION.cff`.

## License

Apache License 2.0.
