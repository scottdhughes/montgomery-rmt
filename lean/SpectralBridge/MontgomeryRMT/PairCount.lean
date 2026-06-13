import SpectralBridge.MontgomeryRMT.Histogram

/-!
# Pair-Count Certificates

Finite natural-number certificates for the number of candidate and accepted
pair sums in the Montgomery-RMT estimator. These statements certify only the
encoded finite count layer.
-/

namespace SpectralBridge
namespace MontgomeryRMT

/-- The triangular number `1 + ... + K`, encoded over natural numbers. -/
def triangularNumber (K : Nat) : Nat :=
  K * (K + 1) / 2

/--
Closed-form candidate count for pair sums with `spacingCount` adjacent spacings
and widths `1, ..., K`, intended for `K <= spacingCount`.
-/
def candidatePairCount (spacingCount K : Nat) : Nat :=
  K * (spacingCount + 1) - triangularNumber K

/-- Nat-safe closed form used for finite candidate pair counts. -/
theorem candidatePairCount_formula (spacingCount K : Nat) :
    candidatePairCount spacingCount K =
      K * (spacingCount + 1) - K * (K + 1) / 2 := by
  rfl

/-- Recursive predicate certifying that every natural-number count is nonnegative. -/
def allNonnegative : List Nat → Prop
  | [] => True
  | x :: xs => 0 ≤ x ∧ allNonnegative xs

/-- Natural-number count vectors are componentwise nonnegative. -/
theorem allNonnegative_nat :
    ∀ xs : List Nat, allNonnegative xs
  | [] => by
      trivial
  | x :: xs => by
      exact ⟨Nat.zero_le x, allNonnegative_nat xs⟩

/-- A histogram total is exactly the sum of its stored count vector. -/
theorem histogram_sum_counts_eq_total (hist : HistogramCertificate) :
    sumNat hist.counts = hist.total := by
  rfl

/--
Finite certificate tying a histogram count vector to a reported accepted-pair
count and a candidate-count upper bound.
-/
structure PairHistogramCertificate where
  label : String
  spacingCount : Nat
  kMax : Nat
  histogram : HistogramCertificate
  acceptedPairCount : Nat
  acceptedPairCount_eq_total : histogram.total = acceptedPairCount
  acceptedPairCount_le_candidate :
    acceptedPairCount ≤ candidatePairCount spacingCount (Nat.min kMax spacingCount)

/-- The accepted-pair count is the sum of the histogram bin counts. -/
theorem pairHistogram_sum_counts_eq_accepted
    (cert : PairHistogramCertificate) :
    sumNat cert.histogram.counts = cert.acceptedPairCount := by
  simpa [HistogramCertificate.total] using cert.acceptedPairCount_eq_total

/-- The accepted-pair count is bounded by the finite candidate-pair count. -/
theorem pairHistogram_accepted_le_candidate
    (cert : PairHistogramCertificate) :
    cert.acceptedPairCount ≤
      candidatePairCount cert.spacingCount (Nat.min cert.kMax cert.spacingCount) :=
  cert.acceptedPairCount_le_candidate

/-- Histogram count vectors in these certificates are componentwise nonnegative. -/
theorem pairHistogram_counts_nonnegative
    (cert : PairHistogramCertificate) :
    allNonnegative cert.histogram.counts :=
  allNonnegative_nat cert.histogram.counts

/-- Default zeta blocks use 9,999 spacings and `kMax = 50`. -/
theorem candidatePairCount_9999_50 :
    candidatePairCount 9999 (Nat.min 50 9999) = 498725 := by
  native_decide

/-- The default finite GUE/GOE controls here use 1,175 spacings and `kMax = 50`. -/
theorem candidatePairCount_1175_50 :
    candidatePairCount 1175 (Nat.min 50 1175) = 57525 := by
  native_decide

/-- The default Poisson control here uses 10,000 spacings and `kMax = 50`. -/
theorem candidatePairCount_10000_50 :
    candidatePairCount 10000 (Nat.min 50 10000) = 498775 := by
  native_decide

end MontgomeryRMT
end SpectralBridge
