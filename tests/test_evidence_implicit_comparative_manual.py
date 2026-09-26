from agents.evidence_agent import is_explicit_comparison


def test_implicit_comparative_claim_is_detected():
    claim = (
        "Model A reports 96% accuracy, while Model B reports "
        "91% accuracy on the same dataset."
    )

    assert is_explicit_comparison(claim), (
        "Implicit comparative claim was not detected."
    )

    print("Implicit comparative detection test passed.")


if __name__ == "__main__":
    test_implicit_comparative_claim_is_detected()