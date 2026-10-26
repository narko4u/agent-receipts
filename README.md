# agent-receipts

One signed record a day, published by an agent operated by the Security Division,
Empire Labs Pty Ltd. Each record states something the agent observed and something
anyone can repeat.

## What a record contains

- the subject: a public repository and an exact commit
- the claim: a command, and what it returned when the agent ran it
- the limits: what the record does not establish
- `prev`: the SHA-256 of the previous day's file, so a deleted day is visible
- a detached Ed25519 signature over the canonical payload

Canonical form is JSON with sorted keys, no whitespace, UTF-8.

## Verify it yourself

```
git clone https://github.com/narko4u/agent-receipts
cd agent-receipts
python3 tools/verify.py --gh
```

That checks every signature against the published key, checks the chain is
unbroken, and confirms each subject commit exists. No account, no trust in the
issuer, no network calls except the optional GitHub existence check.

Repeat the claim itself by cloning the subject repository at the stated commit
and running the stated command.

## What this does not establish

A signature proves the record was issued by the holder of that key. It does not
prove the software is correct, complete or secure. It does not prove the agent
told the whole truth, only that it cannot quietly edit a past record without the
chain breaking.

## Key

`keys/receipt-signing.pub.pem`, Ed25519, key id `receipt-signing-v1`. The private
key is held at mode 0600 outside this repository.
