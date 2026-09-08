# Small manual evaluation set for the RuleLens MVP.
TESTS = [
    ("What attendance is normally required?", "ANSWERED"),
    ("I have 65% attendance and an approved medical exemption. Can I appear?", "ANSWERED"),
    ("I have 45% attendance and a medical exemption. Can I appear?", "ANSWERED"),
    ("What is the international exchange visa sponsorship policy?", "INSUFFICIENT_INFORMATION"),
    ("What attendance applies to the special program?", "CONFLICT"),
]

print("Evaluation cases:")
for question, expected in TESTS:
    print(f"- {expected}: {question}")
print("\nRun these through POST /api/questions/ask and compare status + evidence manually.")
