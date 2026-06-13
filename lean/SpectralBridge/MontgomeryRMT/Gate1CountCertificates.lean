import SpectralBridge.MontgomeryRMT.Gate1DefaultCertificate
import SpectralBridge.MontgomeryRMT.PairCount

/-!
# Gate 1 Count Certificates

Concrete finite histogram certificates for the paper-facing Gate 1 lanes. The
zeta count vectors are recovered from existing CSV density columns exactly; the
control count vectors are recovered from the same exported density columns by
nearest-integer decoding of floating text.
-/

namespace SpectralBridge
namespace MontgomeryRMT

/-- High Odlyzko block `10^12 + 1` through `10^12 + 10^4`, default pair-count vector. -/
def gate1Block1e12PairCounts : List Nat :=
  [2, 4, 32, 45, 75, 104, 147, 172, 262, 270,
   319, 364, 363, 431, 452, 463, 464, 469, 489, 501,
   520, 499, 490, 487, 481, 501, 520, 427, 462, 472,
   475, 473, 505, 473, 479, 499, 487, 537, 511, 459,
   529, 480, 488, 489, 522, 477, 487, 497, 508, 459,
   472, 508, 486, 501, 469, 527, 506, 511, 491, 518,
   536, 508, 470, 506, 514, 480, 528, 486, 518, 466,
   526, 483, 499, 444, 480, 481, 517, 532, 514, 483,
   494, 507, 483, 512, 531, 478, 494, 519, 511, 491,
   464, 478, 502, 477, 499, 552, 514, 497, 477, 476]

/-- High Odlyzko block `10^21 + 1` through `10^21 + 10^4`, default pair-count vector. -/
def gate1Block1e21PairCounts : List Nat :=
  [1, 9, 22, 51, 73, 101, 145, 205, 270, 296,
   310, 354, 393, 421, 432, 452, 472, 481, 471, 506,
   485, 489, 528, 519, 466, 481, 457, 484, 481, 462,
   448, 472, 512, 479, 504, 509, 497, 492, 486, 496,
   490, 478, 521, 483, 521, 501, 497, 495, 503, 498,
   488, 517, 509, 481, 465, 506, 529, 504, 485, 475,
   460, 499, 472, 501, 490, 506, 532, 505, 500, 471,
   502, 524, 480, 473, 481, 486, 521, 517, 496, 479,
   511, 483, 547, 522, 482, 488, 483, 466, 532, 513,
   533, 493, 498, 512, 493, 446, 491, 517, 515, 495]

/-- Default finite GUE control pair-count vector. -/
def gate1GuePairCounts : List Nat :=
  [1, 1, 3, 9, 10, 12, 19, 22, 24, 32,
   34, 37, 42, 58, 49, 44, 51, 67, 61, 68,
   56, 58, 50, 65, 56, 56, 56, 57, 67, 68,
   55, 56, 51, 59, 57, 47, 63, 51, 67, 49,
   72, 55, 69, 62, 50, 38, 64, 54, 66, 81,
   51, 51, 49, 69, 66, 45, 49, 55, 48, 55,
   63, 64, 51, 56, 74, 66, 65, 63, 58, 58,
   58, 51, 64, 75, 52, 55, 62, 47, 54, 50,
   56, 61, 54, 70, 56, 64, 54, 78, 66, 50,
   64, 54, 53, 64, 51, 60, 62, 63, 59, 57]

/-- Default finite GOE contrast-control pair-count vector. -/
def gate1GoePairCounts : List Nat :=
  [1, 5, 9, 22, 19, 31, 38, 30, 43, 44,
   46, 47, 42, 47, 33, 35, 58, 43, 66, 51,
   50, 55, 57, 50, 48, 55, 52, 61, 57, 60,
   59, 67, 56, 57, 56, 61, 61, 51, 63, 57,
   62, 69, 61, 56, 56, 50, 52, 52, 63, 56,
   67, 56, 50, 53, 54, 53, 50, 66, 54, 54,
   47, 61, 57, 61, 66, 63, 71, 46, 58, 66,
   54, 46, 77, 50, 60, 56, 59, 52, 60, 47,
   56, 65, 55, 61, 63, 71, 41, 58, 72, 50,
   51, 70, 63, 65, 53, 71, 44, 68, 58, 63]

/-- Default finite Poisson negative-control pair-count vector. -/
def gate1PoissonPairCounts : List Nat :=
  [535, 468, 504, 484, 521, 482, 488, 544, 493, 493,
   487, 516, 499, 472, 519, 488, 524, 476, 518, 529,
   525, 525, 492, 476, 525, 464, 490, 532, 538, 493,
   539, 502, 497, 509, 492, 512, 486, 489, 481, 498,
   469, 508, 533, 516, 476, 502, 507, 510, 529, 491,
   502, 476, 446, 521, 481, 503, 511, 508, 512, 492,
   510, 520, 501, 484, 493, 502, 476, 495, 506, 523,
   469, 503, 517, 486, 476, 489, 471, 498, 520, 515,
   507, 489, 539, 498, 471, 499, 507, 494, 493, 527,
   490, 461, 503, 493, 477, 507, 519, 487, 498, 490]

def gate1Block1e12Histogram : HistogramCertificate where
  binCount := 100
  counts := gate1Block1e12PairCounts
  counts_length := by
    native_decide

def gate1Block1e21Histogram : HistogramCertificate where
  binCount := 100
  counts := gate1Block1e21PairCounts
  counts_length := by
    native_decide

def gate1GueHistogram : HistogramCertificate where
  binCount := 100
  counts := gate1GuePairCounts
  counts_length := by
    native_decide

def gate1GoeHistogram : HistogramCertificate where
  binCount := 100
  counts := gate1GoePairCounts
  counts_length := by
    native_decide

def gate1PoissonHistogram : HistogramCertificate where
  binCount := 100
  counts := gate1PoissonPairCounts
  counts_length := by
    native_decide

def gate1DefaultPairHistogramCertificate : PairHistogramCertificate where
  label := "gate0_default"
  spacingCount := 9999
  kMax := 50
  histogram := gate1DefaultHistogram
  acceptedPairCount := 44927
  acceptedPairCount_eq_total := by
    native_decide
  acceptedPairCount_le_candidate := by
    native_decide

def gate1Block1e12PairHistogramCertificate : PairHistogramCertificate where
  label := "block_1e12_10k"
  spacingCount := 9999
  kMax := 50
  histogram := gate1Block1e12Histogram
  acceptedPairCount := 45037
  acceptedPairCount_eq_total := by
    native_decide
  acceptedPairCount_le_candidate := by
    native_decide

def gate1Block1e21PairHistogramCertificate : PairHistogramCertificate where
  label := "block_1e21_10k"
  spacingCount := 9999
  kMax := 50
  histogram := gate1Block1e21Histogram
  acceptedPairCount := 45073
  acceptedPairCount_eq_total := by
    native_decide
  acceptedPairCount_le_candidate := by
    native_decide

def gate1GuePairHistogramCertificate : PairHistogramCertificate where
  label := "gue"
  spacingCount := 1175
  kMax := 50
  histogram := gate1GueHistogram
  acceptedPairCount := 5319
  acceptedPairCount_eq_total := by
    native_decide
  acceptedPairCount_le_candidate := by
    native_decide

def gate1GoePairHistogramCertificate : PairHistogramCertificate where
  label := "goe"
  spacingCount := 1175
  kMax := 50
  histogram := gate1GoeHistogram
  acceptedPairCount := 5332
  acceptedPairCount_eq_total := by
    native_decide
  acceptedPairCount_le_candidate := by
    native_decide

def gate1PoissonPairHistogramCertificate : PairHistogramCertificate where
  label := "poisson"
  spacingCount := 10000
  kMax := 50
  histogram := gate1PoissonHistogram
  acceptedPairCount := 50001
  acceptedPairCount_eq_total := by
    native_decide
  acceptedPairCount_le_candidate := by
    native_decide

/-- All six paper-facing default histograms have 100 bins. -/
theorem gate1PaperFacingHistogram_binCounts :
    gate1DefaultHistogram.binCount = 100 ∧
    gate1Block1e12Histogram.binCount = 100 ∧
    gate1Block1e21Histogram.binCount = 100 ∧
    gate1GueHistogram.binCount = 100 ∧
    gate1GoeHistogram.binCount = 100 ∧
    gate1PoissonHistogram.binCount = 100 := by
  native_decide

/-- Default low-block accepted count equals the sum of its encoded histogram bins. -/
theorem gate1Default_sum_counts_eq_accepted :
    sumNat gate1DefaultPairCounts = 44927 := by
  native_decide

theorem gate1Block1e12_sum_counts_eq_accepted :
    sumNat gate1Block1e12PairCounts = 45037 := by
  native_decide

theorem gate1Block1e21_sum_counts_eq_accepted :
    sumNat gate1Block1e21PairCounts = 45073 := by
  native_decide

theorem gate1Gue_sum_counts_eq_accepted :
    sumNat gate1GuePairCounts = 5319 := by
  native_decide

theorem gate1Goe_sum_counts_eq_accepted :
    sumNat gate1GoePairCounts = 5332 := by
  native_decide

theorem gate1Poisson_sum_counts_eq_accepted :
    sumNat gate1PoissonPairCounts = 50001 := by
  native_decide

theorem gate1Default_accepted_le_candidate :
    gate1DefaultPairHistogramCertificate.acceptedPairCount ≤
      candidatePairCount 9999 (Nat.min 50 9999) :=
  pairHistogram_accepted_le_candidate gate1DefaultPairHistogramCertificate

theorem gate1Block1e12_accepted_le_candidate :
    gate1Block1e12PairHistogramCertificate.acceptedPairCount ≤
      candidatePairCount 9999 (Nat.min 50 9999) :=
  pairHistogram_accepted_le_candidate gate1Block1e12PairHistogramCertificate

theorem gate1Block1e21_accepted_le_candidate :
    gate1Block1e21PairHistogramCertificate.acceptedPairCount ≤
      candidatePairCount 9999 (Nat.min 50 9999) :=
  pairHistogram_accepted_le_candidate gate1Block1e21PairHistogramCertificate

theorem gate1Gue_accepted_le_candidate :
    gate1GuePairHistogramCertificate.acceptedPairCount ≤
      candidatePairCount 1175 (Nat.min 50 1175) :=
  pairHistogram_accepted_le_candidate gate1GuePairHistogramCertificate

theorem gate1Goe_accepted_le_candidate :
    gate1GoePairHistogramCertificate.acceptedPairCount ≤
      candidatePairCount 1175 (Nat.min 50 1175) :=
  pairHistogram_accepted_le_candidate gate1GoePairHistogramCertificate

theorem gate1Poisson_accepted_le_candidate :
    gate1PoissonPairHistogramCertificate.acceptedPairCount ≤
      candidatePairCount 10000 (Nat.min 50 10000) :=
  pairHistogram_accepted_le_candidate gate1PoissonPairHistogramCertificate

theorem gate1PaperFacingPairCounts_nonnegative :
    allNonnegative gate1DefaultPairCounts ∧
    allNonnegative gate1Block1e12PairCounts ∧
    allNonnegative gate1Block1e21PairCounts ∧
    allNonnegative gate1GuePairCounts ∧
    allNonnegative gate1GoePairCounts ∧
    allNonnegative gate1PoissonPairCounts := by
  exact ⟨allNonnegative_nat _,
    allNonnegative_nat _,
    allNonnegative_nat _,
    allNonnegative_nat _,
    allNonnegative_nat _,
    allNonnegative_nat _⟩

end MontgomeryRMT
end SpectralBridge
