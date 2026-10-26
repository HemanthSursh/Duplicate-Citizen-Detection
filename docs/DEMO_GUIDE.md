# Three-minute college demonstration

Use fictional details only. Start with a fresh local database so the counts below match.

## 0:00 - Explain the purpose

"This project detects repeated citizen records. SHA-256 finds identical normalized details. RapidFuzz finds similar names and addresses. A person reviews each candidate; nothing is automatically merged."

## 0:20 - Load the demo

Open **Demo data** in the sidebar and click **Load fictional demo**. The dashboard now shows 8 records, 1 exact candidate pair and 2 probable candidate pairs. Explain that these are live SQLite results and that candidate counts mean pairs awaiting review, not unique citizens.

Click a citizen's name on the dashboard. Show the full profile and clearly fictional Aadhaar/driving-licence references. Explain that the references are display-only, not verified, and are not part of matching.

## 0:45 - Show exact matching

Open **Duplicate review**. Choose the exact Aarav Demo pair. Show the four identical normalized fields. Click either citizen name to open the profile, then expand Internal record details if you want to explain the different internal IDs. The weighted score is 100/100. Open **How matching works** to explain sorted-key JSON followed by SHA-256.

## 1:15 - Show probable matching

Choose the Mira Sample / Meera Sample pair. The name and address have small differences, while the birthday and phone agree. Show each field score and its weight. Explain that the score is a rule-based similarity number, not a probability of being the same person.

## 1:40 - Show safe registration

Open **Register citizen** and enter:

- Full name: `Aarav Demo`
- Date of birth: `2001-05-12`
- Phone: `0000000101`
- Address: `14 Example Lane, Demo Nagar`

Click **Check for duplicates**. The error **Phone number already exists.** appears and no save is offered. This is the explicit phone-uniqueness rule. Now change the phone to fictional `0000000999` and check again. The other identical fields produce probable candidates. Click **Continue to review** to show that keeping a separate record with a different phone needs an explicit checkbox and reason. Then click **Cancel** so this demonstration does not add extra records.

## 2:15 - Save a human decision

Return to **Duplicate review**, select the exact pair, choose **Confirmed duplicate**, add `Same four fictional details after normalization`, and save the review decision. Return to the dashboard. The pending exact count drops to zero; total records remain eight. The decision is still visible under **Reviewed**.

## 2:45 - Explain the limits

"This is a local college demo. The fuzzy weights are simple screening rules. It can miss duplicates or flag different people with shared details. It has no production security or identity-verification claim, and uses fictional data only."

## Quick viva answers

**Why JSON instead of joining with a separator?** Named, sorted JSON fields give a stable, unambiguous representation even if a field contains a separator character.

**Why index the fingerprint?** SQLite can look up a hash through its index rather than scanning every stored hash.

**Why is the fingerprint index not unique?** Existing records and intentionally duplicated demo fixtures are preserved. New same-phone registrations are blocked by a transaction-time phone check. Similarity-only candidates with a different phone can still be kept after human review.

**Why SHA-256 and RapidFuzz?** Hashing finds identical normalized values. Fuzzy matching handles small text differences. They solve different parts of the problem.

**What happens to records after review?** They remain unchanged. Only a pair decision and review note are saved.

**Does hashing protect personal data?** No. The original fields remain in SQLite. The hash is for matching, not encryption.
