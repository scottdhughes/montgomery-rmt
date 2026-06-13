import SpectralBridge.MontgomeryRMT.RMSResidual

/-!
# Finite Estimator Certificates

A compact certificate format for the exact finite layer: binned pair counts and
encoded squared residuals. This does not certify the source zero data or the
floating-point values in the paper; it gives a Lean-checkable target for future
generated certificates.
-/

namespace SpectralBridge
namespace MontgomeryRMT

/-- A finite estimator certificate for a fixed bin count. -/
structure FiniteEstimatorCertificate where
  binCount : Nat
  pairCounts : List Nat
  residualSquares : List Nat
  pairCounts_length : pairCounts.length = binCount
  residualSquares_length : residualSquares.length = binCount
  reportedPairTotal : Nat
  pair_total_matches : sumNat pairCounts = reportedPairTotal
  reportedResidualNumerator : Nat
  residual_numerator_matches :
    residualNumerator residualSquares = reportedResidualNumerator

/-- A certificate carries the stated number of pair-count bins. -/
theorem certificate_pairCounts_length (cert : FiniteEstimatorCertificate) :
    cert.pairCounts.length = cert.binCount :=
  cert.pairCounts_length

/-- A certificate carries the stated number of residual-square bins. -/
theorem certificate_residualSquares_length (cert : FiniteEstimatorCertificate) :
    cert.residualSquares.length = cert.binCount :=
  cert.residualSquares_length

/-- The reported pair total is definitionally checked against the count vector. -/
theorem certificate_pair_total_matches (cert : FiniteEstimatorCertificate) :
    sumNat cert.pairCounts = cert.reportedPairTotal :=
  cert.pair_total_matches

/-- The reported residual numerator is checked against the residual-square vector. -/
theorem certificate_residual_numerator_matches
    (cert : FiniteEstimatorCertificate) :
    residualNumerator cert.residualSquares = cert.reportedResidualNumerator :=
  cert.residual_numerator_matches

/-- Reported residual numerators are nonnegative in the encoded certificate. -/
theorem certificate_reportedResidualNumerator_nonnegative
    (cert : FiniteEstimatorCertificate) :
    0 ≤ cert.reportedResidualNumerator :=
  Nat.zero_le _

end MontgomeryRMT
end SpectralBridge
