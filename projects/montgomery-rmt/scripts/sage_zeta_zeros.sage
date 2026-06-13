import argparse
import csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if args.n <= 0:
        raise SystemExit("--n must be positive")

    try:
        from sage.databases.odlyzko import zeta_zeros
    except Exception as exc:
        raise SystemExit(f"missing sage Odlyzko zeta database: {exc}")

    zeros = zeta_zeros()
    selected = zeros[: args.n]
    if len(selected) < args.n:
        raise SystemExit(f"requested {args.n} zeros but only got {len(selected)}")

    with open(args.out, "w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["index", "gamma", "source"])
        for index, gamma in enumerate(selected, start=1):
            writer.writerow([index, gamma, "sage_odlyzko_zeta"])


if __name__ == "__main__":
    main()
