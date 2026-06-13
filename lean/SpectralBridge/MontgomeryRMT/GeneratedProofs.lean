import SpectralBridge.MontgomeryRMT.Generated.Gate1GeneratedCounts
import SpectralBridge.MontgomeryRMT.Generated.Gate1GeneratedResiduals
import SpectralBridge.MontgomeryRMT.Generated.Gate1GeneratedSensitivity
import SpectralBridge.MontgomeryRMT.Generated.Gate1GeneratedManifest
import SpectralBridge.MontgomeryRMT.Gate1SensitivityCertificate

/-!
# Proofs Over Generated Montgomery-RMT Certificates

This handwritten file proves finite claims from generated Lean data emitted by
`projects/montgomery-rmt/scripts/export_lean_certificates.py`.
-/

namespace SpectralBridge
namespace MontgomeryRMT

theorem generated_gate0Default_count_sum_matches :
    sumNat Generated.gate1GeneratedGate0DefaultCounts.counts =
      Generated.gate1GeneratedGate0DefaultCounts.acceptedPairCount := by
  native_decide

theorem generated_block1e12_count_sum_matches :
    sumNat Generated.gate1GeneratedBlock1e12Counts.counts =
      Generated.gate1GeneratedBlock1e12Counts.acceptedPairCount := by
  native_decide

theorem generated_block1e21_count_sum_matches :
    sumNat Generated.gate1GeneratedBlock1e21Counts.counts =
      Generated.gate1GeneratedBlock1e21Counts.acceptedPairCount := by
  native_decide

theorem generated_gue_count_sum_matches :
    sumNat Generated.gate1GeneratedGueCounts.counts =
      Generated.gate1GeneratedGueCounts.acceptedPairCount := by
  native_decide

theorem generated_goe_count_sum_matches :
    sumNat Generated.gate1GeneratedGoeCounts.counts =
      Generated.gate1GeneratedGoeCounts.acceptedPairCount := by
  native_decide

theorem generated_poisson_count_sum_matches :
    sumNat Generated.gate1GeneratedPoissonCounts.counts =
      Generated.gate1GeneratedPoissonCounts.acceptedPairCount := by
  native_decide

theorem generated_gate1_count_lengths_match_bins :
    Generated.gate1GeneratedGate0DefaultCounts.counts.length =
      Generated.gate1GeneratedGate0DefaultCounts.binCount ∧
    Generated.gate1GeneratedBlock1e12Counts.counts.length =
      Generated.gate1GeneratedBlock1e12Counts.binCount ∧
    Generated.gate1GeneratedBlock1e21Counts.counts.length =
      Generated.gate1GeneratedBlock1e21Counts.binCount ∧
    Generated.gate1GeneratedGueCounts.counts.length =
      Generated.gate1GeneratedGueCounts.binCount ∧
    Generated.gate1GeneratedGoeCounts.counts.length =
      Generated.gate1GeneratedGoeCounts.binCount ∧
    Generated.gate1GeneratedPoissonCounts.counts.length =
      Generated.gate1GeneratedPoissonCounts.binCount := by
  native_decide

theorem generated_gate0Default_accepted_le_candidate :
    Generated.gate1GeneratedGate0DefaultCounts.acceptedPairCount ≤
      candidatePairCount
        Generated.gate1GeneratedGate0DefaultCounts.spacingCount
        (Nat.min
          Generated.gate1GeneratedGate0DefaultCounts.kMax
          Generated.gate1GeneratedGate0DefaultCounts.spacingCount) := by
  native_decide

theorem generated_block1e12_accepted_le_candidate :
    Generated.gate1GeneratedBlock1e12Counts.acceptedPairCount ≤
      candidatePairCount
        Generated.gate1GeneratedBlock1e12Counts.spacingCount
        (Nat.min
          Generated.gate1GeneratedBlock1e12Counts.kMax
          Generated.gate1GeneratedBlock1e12Counts.spacingCount) := by
  native_decide

theorem generated_block1e21_accepted_le_candidate :
    Generated.gate1GeneratedBlock1e21Counts.acceptedPairCount ≤
      candidatePairCount
        Generated.gate1GeneratedBlock1e21Counts.spacingCount
        (Nat.min
          Generated.gate1GeneratedBlock1e21Counts.kMax
          Generated.gate1GeneratedBlock1e21Counts.spacingCount) := by
  native_decide

theorem generated_gue_accepted_le_candidate :
    Generated.gate1GeneratedGueCounts.acceptedPairCount ≤
      candidatePairCount
        Generated.gate1GeneratedGueCounts.spacingCount
        (Nat.min
          Generated.gate1GeneratedGueCounts.kMax
          Generated.gate1GeneratedGueCounts.spacingCount) := by
  native_decide

theorem generated_goe_accepted_le_candidate :
    Generated.gate1GeneratedGoeCounts.acceptedPairCount ≤
      candidatePairCount
        Generated.gate1GeneratedGoeCounts.spacingCount
        (Nat.min
          Generated.gate1GeneratedGoeCounts.kMax
          Generated.gate1GeneratedGoeCounts.spacingCount) := by
  native_decide

theorem generated_poisson_accepted_le_candidate :
    Generated.gate1GeneratedPoissonCounts.acceptedPairCount ≤
      candidatePairCount
        Generated.gate1GeneratedPoissonCounts.spacingCount
        (Nat.min
          Generated.gate1GeneratedPoissonCounts.kMax
          Generated.gate1GeneratedPoissonCounts.spacingCount) := by
  native_decide

def generatedEncodedDGate0Default : Nat :=
  Generated.gate1GeneratedGate0DefaultResidual.score

def generatedEncodedDBlock1e12 : Nat :=
  Generated.gate1GeneratedBlock1e12Residual.score

def generatedEncodedDBlock1e21 : Nat :=
  Generated.gate1GeneratedBlock1e21Residual.score

theorem generated_default_zeta_residual_chain :
    generatedEncodedDGate0Default > generatedEncodedDBlock1e12 ∧
    generatedEncodedDBlock1e12 > generatedEncodedDBlock1e21 := by
  native_decide

theorem generated_primary_high_vs_low_wins_eq_27 :
    countTrue Generated.generatedPrimaryHighVsLowSummary.values = 27 ∧
    Generated.generatedPrimaryHighVsLowSummary.values.length = 27 := by
  native_decide

theorem generated_block1e21_vs_low_wins_eq_27 :
    countTrue Generated.generatedBlock1e21VsLowSummary.values = 27 ∧
    Generated.generatedBlock1e21VsLowSummary.values.length = 27 := by
  native_decide

theorem generated_strict_three_block_monotone_eq_18_of_27 :
    countTrue Generated.generatedStrictThreeBlockMonotoneSummary.values = 18 ∧
    Generated.generatedStrictThreeBlockMonotoneSummary.values.length = 27 := by
  native_decide

theorem generated_gue_beats_poisson_eq_156_of_162 :
    countTrue Generated.generatedGueBeatsPoissonSummary.values = 156 ∧
    Generated.generatedGueBeatsPoissonSummary.values.length = 162 := by
  native_decide

end MontgomeryRMT
end SpectralBridge
