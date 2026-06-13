import SpectralBridge.MontgomeryRMT.Histogram

/-!
# Gate 1 Default Histogram Certificate

This file records one concrete finite artifact from the default low-block
pair-correlation CSV:

`projects/montgomery-rmt/data/processed/gate1_gate0_default_paircorr.csv`

The pair counts are recovered from the published density column using the
default normalization `density = count / (10000 * 0.05)`. Lean checks the bin
count and total accepted pair count. This does not certify the zeta-zero data
or the floating-point RMS residual.
-/

namespace SpectralBridge
namespace MontgomeryRMT

/-- Default low-block finite pair-count vector, recovered from the CSV density column. -/
def gate1DefaultPairCounts : List Nat :=
  [2, 3, 12, 25, 54, 67, 112, 170, 189, 244,
   304, 338, 396, 409, 519, 515, 507, 498, 503, 533,
   497, 509, 467, 471, 492, 458, 459, 462, 510, 451,
   484, 482, 516, 489, 514, 492, 498, 547, 454, 512,
   506, 482, 498, 464, 509, 436, 492, 497, 528, 478,
   497, 471, 494, 526, 508, 517, 489, 514, 476, 486,
   488, 517, 488, 493, 495, 494, 475, 474, 496, 514,
   501, 497, 482, 497, 524, 504, 519, 532, 508, 470,
   474, 464, 470, 490, 482, 502, 478, 531, 523, 484,
   522, 519, 525, 502, 510, 484, 538, 475, 446, 508]

/-- Histogram certificate for the default low-block pair-count vector. -/
def gate1DefaultHistogram : HistogramCertificate where
  binCount := 100
  counts := gate1DefaultPairCounts
  counts_length := by
    native_decide

/-- The default low-block histogram has 100 finite bins. -/
theorem gate1DefaultPairCounts_length :
    gate1DefaultPairCounts.length = 100 := by
  native_decide

/-- The default low-block histogram contains 44,927 accepted finite pair sums. -/
theorem gate1DefaultHistogram_total :
    gate1DefaultHistogram.total = 44927 := by
  native_decide

end MontgomeryRMT
end SpectralBridge
