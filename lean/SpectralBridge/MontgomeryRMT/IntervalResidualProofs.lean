import SpectralBridge.MontgomeryRMT.Generated.Gate1IntervalResiduals

/-!
# Interval Residual Proofs for Montgomery-RMT

This file proves finite arithmetic claims from Arb-backed generated interval
certificates. The generated intervals are trusted inputs; Lean checks their
well-formedness and the resulting squared-residual ordering.
-/

namespace SpectralBridge
namespace MontgomeryRMT

def intervalResidualGate0Lower : Nat :=
  Generated.gate1IntervalGate0DefaultResidual.lower

def intervalResidualGate0Upper : Nat :=
  Generated.gate1IntervalGate0DefaultResidual.upper

def intervalResidual1e12Lower : Nat :=
  Generated.gate1IntervalBlock1e12Residual.lower

def intervalResidual1e12Upper : Nat :=
  Generated.gate1IntervalBlock1e12Residual.upper

def intervalResidual1e21Lower : Nat :=
  Generated.gate1IntervalBlock1e21Residual.lower

def intervalResidual1e21Upper : Nat :=
  Generated.gate1IntervalBlock1e21Residual.upper

theorem interval_denominators_positive :
    Generated.gate1SineKernelIntervalScale > 0 ∧
    Generated.gate1IntervalGate0DefaultResidual.denominator > 0 ∧
    Generated.gate1IntervalBlock1e12Residual.denominator > 0 ∧
    Generated.gate1IntervalBlock1e21Residual.denominator > 0 := by
  native_decide

theorem interval_sine_kernel_bounds_well_formed :
    Generated.gate1SineKernelIntervals.length = Generated.gate1IntervalBinCount ∧
    Generated.gate1SineKernelIntervalsWellFormed = true := by
  native_decide

theorem interval_residual_bounds_well_formed :
    Generated.gate1IntervalResidualsWellFormed = true := by
  native_decide

theorem interval_residuals_have_common_denominator :
    Generated.gate1IntervalGate0DefaultResidual.denominator =
      Generated.gate1IntervalBlock1e12Residual.denominator ∧
    Generated.gate1IntervalBlock1e12Residual.denominator =
      Generated.gate1IntervalBlock1e21Residual.denominator := by
  native_decide

/--
Default finite zeta residual chain from Arb-backed sine-kernel interval
certificates. The comparison is over squared-residual sums, avoiding square
roots.
-/
theorem interval_default_zeta_residual_chain :
    intervalResidualGate0Lower > intervalResidual1e12Upper ∧
    intervalResidual1e12Lower > intervalResidual1e21Upper := by
  native_decide

end MontgomeryRMT
end SpectralBridge
