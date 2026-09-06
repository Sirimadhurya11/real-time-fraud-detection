from decimal import Decimal


# =========================================================
# FRAUD DETECTION CONFIGURATION
# =========================================================

HIGH_AMOUNT_THRESHOLD = Decimal("50000")
MEDIUM_AMOUNT_THRESHOLD = Decimal("10000")

HIGH_RISK_LOCATIONS = {
    "unknown",
    "restricted",
    "high_risk"
}


# =========================================================
# CALCULATE FRAUD RISK
# =========================================================

def calculate_fraud_risk(
    amount: Decimal,
    location: str,
    transaction_count_last_hour: int = 0
):
    score = 0
    reasons = []

    # -----------------------------------------------------
    # RULE 1 — VERY HIGH TRANSACTION AMOUNT
    # -----------------------------------------------------

    if amount >= HIGH_AMOUNT_THRESHOLD:

        score += 50

        reasons.append(
            "Very high transaction amount"
        )

    # -----------------------------------------------------
    # RULE 2 — HIGH TRANSACTION AMOUNT
    # -----------------------------------------------------

    elif amount >= MEDIUM_AMOUNT_THRESHOLD:

        score += 25

        reasons.append(
            "High transaction amount"
        )

    # -----------------------------------------------------
    # RULE 3 — HIGH-RISK LOCATION
    # -----------------------------------------------------

    normalized_location = location.strip().lower()

    if normalized_location in HIGH_RISK_LOCATIONS:

        score += 30

        reasons.append(
            "Transaction originated from a high-risk location"
        )

    # -----------------------------------------------------
    # RULE 4 — TRANSACTION VELOCITY
    # -----------------------------------------------------

    if transaction_count_last_hour >= 10:

        score += 40

        reasons.append(
            "Unusually high transaction frequency"
        )

    elif transaction_count_last_hour >= 5:

        score += 20

        reasons.append(
            "High transaction frequency"
        )

    # -----------------------------------------------------
    # LIMIT SCORE
    # -----------------------------------------------------

    score = min(score, 100)

    # -----------------------------------------------------
    # DETERMINE RISK LEVEL
    # -----------------------------------------------------

    if score >= 70:

        risk_level = "HIGH"
        decision = "BLOCK"
        is_fraud = True

    elif score >= 40:

        risk_level = "MEDIUM"
        decision = "REVIEW"
        is_fraud = False

    else:

        risk_level = "LOW"
        decision = "APPROVE"
        is_fraud = False

    # -----------------------------------------------------
    # DEFAULT REASON
    # -----------------------------------------------------

    if not reasons:

        reasons.append(
            "No suspicious activity detected"
        )

    return {

        "risk_score": score,

        "risk_level": risk_level,

        "decision": decision,

        "is_fraud": is_fraud,

        "reasons": reasons
    }