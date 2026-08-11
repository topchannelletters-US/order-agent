# Status Rules

Use the furthest confirmed status supported by the latest email evidence.

## Main Statuses

- `Awaiting Estimate`: customer requested a quote/estimate/pricing, but TCL has not sent price yet.
- `Estimate`: TCL has sent pricing/estimate, but there is no later customer approval.
- `Design`: rendering, artwork, CAD, measurements, colors, revisions, or approval discussion.
- `Permit`: permit, city review, landlord approval, contractor registration, COI, or bond work needed before production/install.
- `Production`: materials ordered, fabrication started, production file sent, manufacturing in progress.
- `Installation`: installation scheduled, crew dispatched, installation happening, or install coordination underway.
- `Payment Awaiting`: invoice sent, deposit/final payment requested, payment pending.
- `Completed`: installation completed, customer accepted, payment received, or project closed.
- `Withdraw`: customer cancelled, rejected estimate, abandoned project, or project transferred away.

## Additional Flags

- `Need to Issue Invoice`: work has progressed far enough that invoice should be created but has not been sent.
- `Need to Process`: internal action is required.
- `Follow Up`: waiting on customer approval, response, payment, dimensions, files, or decision.

## Priority

`Withdraw` overrides all other statuses. Otherwise use the furthest confirmed stage:

Awaiting Estimate -> Estimate -> Design -> Permit -> Production -> Installation -> Payment Awaiting -> Completed

Never infer a later status from old messages if newer messages contradict it.

## Estimate Workflow Rule

TCL's common quoting flow is:

1. Customer asks for an estimate, pricing, quote, RFQ, or inquiry.
2. TCL asks the designer for an Illustrator/source file or internal layout so the job can be priced.
3. Charles/boss replies to the customer with price.

Steps 1-2 are `Awaiting Estimate`.

Step 3 is `Estimate`.

Do not upgrade to `Design`, `Production`, or `Installation` only because:

- the customer provided artwork, drawings, dimensions, or an Illustrator file for pricing;
- TCL created a mockup only to support the quote;
- the quoted scope mentions installation or installation cost;
- TCL replied with pricing;
- the customer says "thanks", "I'll stay in touch", or asks a price clarification.

Upgrade beyond `Estimate` only when a later email clearly confirms progress, such as:

- customer approves the price or says to proceed;
- deposit/payment is requested or received;
- permit work begins for the accepted job;
- production file is finalized for fabrication after approval;
- installation is scheduled for an approved job.
