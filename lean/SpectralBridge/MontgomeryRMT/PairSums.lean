import SpectralBridge.MontgomeryRMT.FiniteBlock

/-!
# Pair Sums

Finite pair-sum bookkeeping for encoded spacing lists. The index structure
records the exact finite range used by the computational estimator:
positive width, bounded by `kMax`, and contained in the spacing list.
-/

namespace SpectralBridge
namespace MontgomeryRMT

/-- A small explicit natural-number list sum. -/
def sumNat : List Nat → Nat
  | [] => 0
  | x :: xs => x + sumNat xs

@[simp]
theorem sumNat_nil : sumNat [] = 0 := rfl

@[simp]
theorem sumNat_cons (x : Nat) (xs : List Nat) :
    sumNat (x :: xs) = x + sumNat xs := rfl

/-- Recursive positivity predicate for encoded positive lists. -/
def allPositive : List Nat → Prop
  | [] => True
  | x :: xs => 0 < x ∧ allPositive xs

/-- A nonempty list of positive natural numbers has positive sum. -/
theorem sumNat_pos_of_allPositive :
    ∀ xs : List Nat, allPositive xs → 0 < xs.length → 0 < sumNat xs
  | [], _hpos, hlen => by
      cases hlen
  | x :: xs, hpos, _hlen => by
      simp [sumNat, allPositive] at hpos ⊢
      exact Nat.lt_of_lt_of_le hpos.1 (Nat.le_add_right x (sumNat xs))

/--
A certified finite pair-sum index.

For a spacing list of length `spacingCount`, `start` is zero-based and `width`
corresponds to the paper's positive `k`.
-/
structure PairIndex (spacingCount kMax : Nat) where
  start : Nat
  width : Nat
  width_pos : 0 < width
  width_le_kMax : width ≤ kMax
  within_spacings : start + width ≤ spacingCount

/-- The width of a certified pair-sum index is in the configured range. -/
theorem pairIndex_width_in_range {spacingCount kMax : Nat}
    (idx : PairIndex spacingCount kMax) :
    0 < idx.width ∧ idx.width ≤ kMax :=
  ⟨idx.width_pos, idx.width_le_kMax⟩

/-- A certified pair-sum index starts inside the spacing list. -/
theorem pairIndex_start_lt_spacingCount {spacingCount kMax : Nat}
    (idx : PairIndex spacingCount kMax) :
    idx.start < spacingCount :=
  Nat.lt_of_lt_of_le (Nat.lt_add_of_pos_right idx.width_pos) idx.within_spacings

/-- The encoded finite pair sum beginning at `start` with positive `width`. -/
def pairSum (spacings : List Nat) (start width : Nat) : Nat :=
  sumNat ((spacings.drop start).take width)

/-- Evaluate a pair sum at a certified index. -/
def pairSumAtIndex (spacings : List Nat) {kMax : Nat}
    (idx : PairIndex spacings.length kMax) : Nat :=
  pairSum spacings idx.start idx.width

/-- Encoded pair sums are natural numbers, hence nonnegative. -/
theorem pairSum_nonnegative (spacings : List Nat) (start width : Nat) :
    0 ≤ pairSum spacings start width :=
  Nat.zero_le _

/--
If the selected finite window is nonempty and every encoded spacing in it is
positive, then the encoded pair sum is positive.
-/
theorem pairSum_pos_of_allPositive_window
    (spacings : List Nat) (start width : Nat)
    (hpos : allPositive ((spacings.drop start).take width))
    (hlen : 0 < ((spacings.drop start).take width).length) :
    0 < pairSum spacings start width := by
  unfold pairSum
  exact sumNat_pos_of_allPositive ((spacings.drop start).take width) hpos hlen

end MontgomeryRMT
end SpectralBridge
