import SpectralBridge.MontgomeryRMT.PairSums

/-!
# Histogram Bookkeeping

Build-checked finite histogram certificates. This file certifies structural
properties of binned count vectors, not floating-point bin arithmetic.
-/

namespace SpectralBridge
namespace MontgomeryRMT

/-- A finite histogram certificate with a declared number of bins. -/
structure HistogramCertificate where
  binCount : Nat
  counts : List Nat
  counts_length : counts.length = binCount

/-- Total encoded count stored in a histogram certificate. -/
def HistogramCertificate.total (hist : HistogramCertificate) : Nat :=
  sumNat hist.counts

/-- Histogram totals are natural numbers, hence nonnegative. -/
theorem histogram_total_nonnegative (hist : HistogramCertificate) :
    0 ≤ hist.total :=
  Nat.zero_le _

/-- An abstract discrete bin assignment. -/
def inDiscreteBin (binOf : Nat → Nat) (x j : Nat) : Prop :=
  binOf x = j

/-- A deterministic discrete bin assignment gives a unique bin. -/
theorem inDiscreteBin_unique (binOf : Nat → Nat) (x j k : Nat)
    (hj : inDiscreteBin binOf x j)
    (hk : inDiscreteBin binOf x k) :
    j = k := by
  unfold inDiscreteBin at hj hk
  rw [← hj, hk]

end MontgomeryRMT
end SpectralBridge
