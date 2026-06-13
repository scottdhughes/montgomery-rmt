import Mathlib.Data.Nat.Basic

/-!
# Finite Blocks

Build-checked finite bookkeeping for encoded Montgomery--RMT zero blocks.

This file intentionally works with natural-number encoded data. It certifies
list-level structure used by downstream finite certificates; it does not
certify that any decimal ordinate is a zero of the zeta function.
-/

namespace SpectralBridge
namespace MontgomeryRMT

/-- A finite block of encoded ordinates or normalized spacings. -/
structure FiniteBlock where
  values : List Nat

/-- Adjacent nonnegative gaps in a finite encoded block. -/
def adjacentGaps : List Nat → List Nat
  | [] => []
  | [_] => []
  | x :: y :: rest => (y - x) :: adjacentGaps (y :: rest)

@[simp]
theorem adjacentGaps_nil : adjacentGaps [] = [] := rfl

@[simp]
theorem adjacentGaps_singleton (x : Nat) : adjacentGaps [x] = [] := rfl

/-- A block with `N` entries has `N - 1` adjacent gaps. -/
theorem length_adjacentGaps : ∀ values : List Nat,
    (adjacentGaps values).length = values.length - 1
  | [] => by
      simp [adjacentGaps]
  | [_] => by
      simp [adjacentGaps]
  | x :: y :: rest => by
      simp [adjacentGaps, length_adjacentGaps (y :: rest)]

/-- The adjacent-gap length theorem specialized to `FiniteBlock`. -/
theorem finiteBlock_adjacentGaps_length (block : FiniteBlock) :
    (adjacentGaps block.values).length = block.values.length - 1 :=
  length_adjacentGaps block.values

end MontgomeryRMT
end SpectralBridge
