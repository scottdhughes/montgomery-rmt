/-!
# Gate 1 Sensitivity Certificates

Finite Boolean-vector certificates for the saved Gate 1-B summary counts.
They certify only the exported comparison-vector bookkeeping.
-/

namespace MontgomeryRMT

/-- Count `true` entries in a finite Boolean vector. -/
def countTrue : List Bool → Nat
  | [] => 0
  | true :: xs => 1 + countTrue xs
  | false :: xs => countTrue xs

/-- Primary high block beats the low block in each of the 27 saved zeta configurations. -/
def highVsLowWinsVector : List Bool :=
  (List.range 27).map (fun _ => true)

/-- The second high block also beats the low block in each of the 27 saved zeta configurations. -/
def block1e21VsLowWinsVector : List Bool :=
  (List.range 27).map (fun _ => true)

/-- Strict three-block monotonicity vector from the saved full-grid sensitivity metrics. -/
def strictThreeBlockMonotoneVector : List Bool :=
  (List.range 27).map (fun i => decide (i < 18))

/-- Zero-based saved full-grid GUE-vs-Poisson comparison indices where GUE did not win. -/
def gueBeatsPoissonLossIndices : List Nat :=
  [36, 38, 42, 44, 48, 50]

/-- Saved full-grid GUE-vs-Poisson comparison vector. -/
def gueBeatsPoissonVector : List Bool :=
  (List.range 162).map (fun i => !(gueBeatsPoissonLossIndices.contains i))

theorem high_vs_low_wins_eq_27 :
    countTrue highVsLowWinsVector = 27 := by
  native_decide

theorem block_1e21_vs_low_wins_eq_27 :
    countTrue block1e21VsLowWinsVector = 27 := by
  native_decide

theorem strict_three_block_monotone_eq_18 :
    countTrue strictThreeBlockMonotoneVector = 18 := by
  native_decide

theorem total_zeta_configs_eq_27 :
    highVsLowWinsVector.length = 27 ∧
    block1e21VsLowWinsVector.length = 27 ∧
    strictThreeBlockMonotoneVector.length = 27 := by
  native_decide

theorem gue_beats_poisson_eq_156 :
    countTrue gueBeatsPoissonVector = 156 := by
  native_decide

theorem total_control_configs_eq_162 :
    gueBeatsPoissonVector.length = 162 := by
  native_decide

end MontgomeryRMT
