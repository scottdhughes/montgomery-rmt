import SpectralBridge.MontgomeryRMT.Histogram

/-!
# Discrete Residual Bookkeeping

The numerical paper reports floating-point RMS residuals. This file certifies
the finite natural-number layer used by exact certificates: nonnegativity of
encoded squared-residual sums and the zero iff every encoded square is zero.
-/

namespace SpectralBridge
namespace MontgomeryRMT

/-- Recursive zero predicate for encoded residual-square lists. -/
def allZero : List Nat → Prop
  | [] => True
  | x :: xs => x = 0 ∧ allZero xs

/-- Encoded residual numerator before division and square root. -/
def residualNumerator (residualSquares : List Nat) : Nat :=
  sumNat residualSquares

/-- Encoded residual numerators are natural numbers, hence nonnegative. -/
theorem residualNumerator_nonnegative (residualSquares : List Nat) :
    0 ≤ residualNumerator residualSquares :=
  Nat.zero_le _

/-- A natural-number sum is zero exactly when each term is zero. -/
theorem sumNat_eq_zero_iff_allZero :
    ∀ xs : List Nat, sumNat xs = 0 ↔ allZero xs
  | [] => by
      simp [sumNat, allZero]
  | x :: xs => by
      simp [sumNat, allZero, sumNat_eq_zero_iff_allZero xs]

/-- The encoded residual numerator vanishes exactly when every square vanishes. -/
theorem residualNumerator_eq_zero_iff_allZero (residualSquares : List Nat) :
    residualNumerator residualSquares = 0 ↔ allZero residualSquares := by
  unfold residualNumerator
  exact sumNat_eq_zero_iff_allZero residualSquares

end MontgomeryRMT
end SpectralBridge
