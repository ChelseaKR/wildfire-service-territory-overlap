# Draft: review packet for the inclusion rule

Status: **draft, not sent, and reviewed by nobody**. No reviewer has been found, no
reviewer has been approached, and this packet has not been shown to anybody outside
this project. When a review happens, its date and its finding go into `PROVENANCE.md`
and the finding is published as a measurement, on the terms in
"What happens to your answer" below.

This packet exists so that the request is answerable. "Read the code and tell us if the
inclusion rule is right" is not a reviewable question. What follows is the bounded
version of it: one question, 24 times, with everything already established attached, so
that a reviewer spends their attention on the part nobody here can settle.

## The question

For each of the 24 outlines listed below:

> Is the California Energy Commission's classification of this outline as an electric
> service territory correct, given how the Commission uses its own `Type` field?

You are checking the publisher's classification. You are not reviewing this project's
code, its geometry, its statistics, or the conclusions it draws. This project reads the
publisher's `Type` field and refuses, deliberately, to make an entity-level judgment of
its own. What is missing is somebody who can say whether the publisher's own field says
what this project reads it as saying.

"I cannot say from the public record" is a real answer to any of the 24, and it is more
useful here than a guess. It will be published as that.

## What the inclusion rule does

The California Energy Commission publishes electric load serving entities in two layers.
Every outline carries a `Type` field, and this retrieval carries six values: `ADMIN`,
`CCA`, `CO-OP`, `IOU`, `POU` and `Tribal`.

The rule is mechanical. Four of the six values are read as a retail electric service
territory, meaning an area within which the entity owns the distribution system a burned
structure was connected to:

- `CO-OP`
- `IOU`
- `POU`
- `Tribal`

Two are excluded, for reasons about what the polygon represents rather than about any
organisation:

- `CCA`. A community choice aggregator is defined at Public Utilities Code section 331.1
  as a local government electricity buyers' programme, and section 366.2 leaves
  metering, billing and delivery with the electrical corporation. Its polygon overlays
  another entity's distribution footprint rather than being one, so counting a record
  into both would count it twice.
- `ADMIN`. A federal power marketing administration, in this data the Western Area Power
  Administration. The mapped area is a marketing and transmission administration area,
  not a retail service territory.

The rule is the publisher's field and not a judgment about any named entity. That was
deliberate, and it is written up in
[ADR 0002, which published outlines are read as service territories](../adr/0002-which-published-outlines-are-service-territories.md).

**The publisher documents none of the six values.** As retrieved, the layer metadata
carries no description on the `Type` field and no coded-value domain, the FGDC record
carries no entity and attribute section, and no data dictionary is attached to either
item. The four expansions above are the conventional reading of the abbreviations, not
the publisher's definition, because the publisher has published no definition. A
separate draft under this directory asks the Commission for one, and it has not been
sent either.

## What has already been measured, so you do not have to argue it

The rule was run against its alternatives over the whole record set: not a sample and
not an argument, but the same 132,520 records placed again under each variant. The
results are published in
[the inclusion-rule section of the report](../../published/REPORT.md), and the short
version is this.

Under the rule as built, 50,167 records, 37.9% of the set, fall inside two or more
published outlines at once.

- Dropping `CO-OP` moves the headline by 0.065 percentage points, and pushes 1,406
  records into "inside no published territory", which is a statement about coverage that
  the dropped entities' own published polygons contradict.
- Dropping `Tribal` changes nothing at all. No record in the file falls inside any
  outline the publisher types as `Tribal`.
- Reading `CCA` as a territory moves the headline by 18.5 percentage points.
- Reading `ADMIN` as a territory moves it by 36.5 percentage points.
- Reading every published type as a territory moves it by 52.5 percentage points.

So the two inclusions this project was least sure of are worth almost nothing to the
figure it leads with, and the two exclusions carry the weight. If your attention is
limited, the exclusions are where it pays. The reasoning is in
[ADR 0006, the inclusion rule measured against its alternatives](../adr/0006-the-inclusion-rule-is-measured-against-its-alternatives.md).

None of that establishes anything about any named entity. It measures what the rule
costs. It is not evidence that the publisher's classification of any particular outline
is right, which is exactly the gap this packet asks you to look at.

## Why the list is 24 and not 59

59 outlines are indexed under the rule as built. 35 of them hold no record at all: 0 of
132,520 records fall inside any of the 35, and placing the whole record set again with
all 35 removed at once changes the outcome of 0 records. Whatever the right
classification of those 35 is, every figure this project publishes is the same either
way, so a finding about them cannot move anything. They are named in
[the report's list of outlines that hold nothing](../../published/REPORT.md) and the
reasoning is in
[ADR 0010, an outline that holds no record is counted, not classified](../adr/0010-an-outline-that-holds-no-record-is-counted-not-classified.md).

That leaves 24, where the same question would matter a great deal. This is a bound on
what a review could change, not a claim that the 35 are correctly classified. Nobody
here has decided that either.

## The 24 outlines that hold records

Name, the publisher's `Type` value, and which of the two published layers the outline
came from. The list is in name order, which is the only order anything is ever presented
in here, and the order carries no meaning: it is not by size, by count, or by how
doubtful anything is.

| Outline, as the publisher names it | Published `Type` | Published layer |
|---|---|---|
| Anza Electric Cooperative, Inc. | CO-OP | Electric Load Serving Entities (Other) |
| City and County of San Francisco - Hetch Hetchy Water and Power | POU | Electric Load Serving Entities (IOU & POU) |
| City of Anaheim Public Utilities Department | POU | Electric Load Serving Entities (IOU & POU) |
| City of Banning Electric Department | POU | Electric Load Serving Entities (IOU & POU) |
| City of Healdsburg Electric Department | POU | Electric Load Serving Entities (IOU & POU) |
| City of Riverside | POU | Electric Load Serving Entities (IOU & POU) |
| City of Shasta Lake | POU | Electric Load Serving Entities (IOU & POU) |
| Lassen Municipal Utility District | POU | Electric Load Serving Entities (IOU & POU) |
| Liberty Utilities | IOU | Electric Load Serving Entities (IOU & POU) |
| Los Angeles Department of Water & Power | POU | Electric Load Serving Entities (IOU & POU) |
| Metropolitan Water District of So. Cal | POU | Electric Load Serving Entities (IOU & POU) |
| Modesto Irrigation District | POU | Electric Load Serving Entities (IOU & POU) |
| PacifiCorp | IOU | Electric Load Serving Entities (IOU & POU) |
| Pacific Gas & Electric Company | IOU | Electric Load Serving Entities (IOU & POU) |
| Pasadena Water & Power | POU | Electric Load Serving Entities (IOU & POU) |
| Plumas-Sierra Rural Electric Cooperative | CO-OP | Electric Load Serving Entities (Other) |
| Power and Water Resource Pooling Authority | POU | Electric Load Serving Entities (IOU & POU) |
| Redding Electric Utility | POU | Electric Load Serving Entities (IOU & POU) |
| Sacramento Municipal Utility District | POU | Electric Load Serving Entities (IOU & POU) |
| San Diego Gas & Electric | IOU | Electric Load Serving Entities (IOU & POU) |
| Southern California Edison | IOU | Electric Load Serving Entities (IOU & POU) |
| Surprise Valley Electrification Corporation | CO-OP | Electric Load Serving Entities (Other) |
| Trinity Public Utilities District | POU | Electric Load Serving Entities (IOU & POU) |
| Turlock Irrigation District | POU | Electric Load Serving Entities (IOU & POU) |

By published type that is 5 `IOU`, 16 `POU` and 3 `CO-OP`. No outline typed `Tribal`
holds a record, so the `Tribal` question cannot move a figure here and is not on this
list.

Names are reproduced exactly as the publisher spells them, punctuation and abbreviations
included, so that a row can be matched back to the source layer without guessing.

## What is deliberately not in this packet, and where to find it

Per-outline record counts are already published and are not restated here, because a
document that copies numbers is a document that goes stale. The table under
[the report's territory section](../../published/REPORT.md) carries, for every one of
the 59 outlines: the published type, how many records are placed inside it alone, how
many are contested between it and another outline, how many distinct incidents those
records come from, what share came from the largest single incident, and how much of its
total sits within 250 metres of the published edge. Read that table beside this one.
Two things that are not there, and never will be:

- **No damage rate for any territory.** Not ordered, not unordered, not side by side. A
  territory's damage figures are driven by which fires burned in it, and where one
  incident supplies most of a territory's records a territory-level rate would be a
  statement about that one fire. That refusal is settled in
  [ADR 0004, no damage rate is published for a territory](../adr/0004-no-damage-rate-is-published-for-a-territory.md),
  and a review cannot reopen it.
- **No infrastructure location, address, parcel or coordinate.** Nothing here reads,
  infers, or publishes the position of any conductor, pole, or substation, and no
  finding will change that.

If your judgment about an outline depends on something in that category, say so and stop
there. The honest outcome is "this cannot be settled from what is published", not a
number invented to fill the gap.

## How to answer

Per outline, in name order, four fields:

1. **Outline**, copied from the table above.
2. **Finding**, one of: `classification correct`, `classification wrong`, or
   `cannot say from the public record`.
3. **Because**, one or two sentences.
4. **Source**, which is either a filing, tariff, code section, or Commission document,
   or else the words `no public source` where the finding rests on professional
   knowledge rather than on a citable record. Both are usable. They are published
   differently.

A worked example of the shape, with a placeholder outline that is not on the list:

- Outline: Example Municipal Utility District.
- Finding: `cannot say from the public record`.
- Because: the entity holds a water right and a distribution franchise under the same
  name, and the published outline does not distinguish them.
- Source: `no public source`.

Those answers are the whole deliverable. They do not need to be a report and they do not
need to be uniform: 24 answers of `cannot say` would be a finding, and a useful one,
because it would establish that the publisher's own field cannot be checked from outside
the publisher.

They can go on issue #52 in this repository, which is where roadmap item 3.3 is tracked,
or by whatever channel suits you better.

## The file to fill, if you would rather send a rule than prose

Prose is fine and is the shorter path. But if your findings amount to a different
reading of the publisher's `Type` field, there is a file that turns that reading
straight into a published measurement, with nobody in between editing code on your
behalf.

It is a small JSON document. `fixtures/inclusion_rule_example.json` in this repository
is a filled-in copy of it, written against the invented test layer rather than the real
one, and the shape is this:

```json
{
  "variant": "a short name for this reading, which becomes the row's name",
  "reviewer_role": "your role, or how you would like to be described",
  "reviewed_on": "2026-01-31",
  "types_read_as_territories": ["CO-OP", "IOU", "POU", "Tribal"],
  "outline_overrides": {
    "Outline, exactly as the publisher names it": {
      "read_as_a_territory": false,
      "reason": "one line, in your words, published as you write it"
    }
  }
}
```

`types_read_as_territories` is the whole rule, not a change to it: list every type your
reading counts, including the ones you agree with. `outline_overrides` is optional and
goes on top of the types, for the case the type field cannot express: one named outline
read out of the rule, or one read into it, with a reason each. `reviewer_role` is a role
rather than a name because the field is published; if you would rather be named, say so
when you send it and it is recorded that way.

Then the build runs your rule to completion over all 132,520 records and publishes it as
one more row:

```
make report INCLUSION_RULES=path/to/your-rule.json
```

Two things it does rather than guess. A rule naming a type or an outline the pinned
retrieval does not carry is refused before anything is measured, naming what it could
not find, so a reading written against last year's layer cannot quietly measure less
than you asked for. And a key it does not recognise is refused rather than ignored, so a
misspelt field is a message and not a silently dropped instruction.

## What happens to your answer

This is the part worth reading before you start, because it changes what you are signing
up for.

**A finding does not edit the inclusion rule.** It lands as a new sensitivity row: the
whole record set placed again under the reading your finding implies, published beside
the rule as built with its denominator, its interval, and its difference from the rule
as built. Nothing is marked better. The rule as built is the reference row and stays the
reference row.

That is the same treatment the original judgment got. The point of the sensitivity
machinery in this project is that a judgment call is published together with what it is
worth, and a reviewer's judgment is a judgment call. Yours will be published as a
measurement of what your reading costs, not applied silently as a correction.

Two consequences follow, and neither is negotiable:

- Your finding will be **published in this repository**, with whatever reasoning you
  give and whatever source you cite. Attribution is yours to set: by name, by role, or
  not at all. Say which when you send the answers, and it is recorded that way.
- Your finding will be published **next to the disagreement**, not instead of it. If you
  say an outline is misclassified and the rule as built keeps reading it as a territory,
  both readings appear, with the difference between them measured over all 132,520
  records. Nobody wins the argument. The reader is shown what the argument is worth.

If the whole review comes back as agreement with the rule as built, that is also
published: as a review that happened, by somebody named, on a stated date, which is
strictly more than this project can say today.

## What this packet does not ask you to do

- It does not ask you to review any code. No line of this project's source is part of
  the question.
- It does not ask you to resolve the overlaps. Where two published outlines cover the
  same ground, this project reports the contest and awards it to nobody, and that is
  settled in
  [ADR 0003, contested ground is reported and never resolved](../adr/0003-contested-ground-is-reported-never-resolved.md).
- It does not ask you to correct any boundary. The publisher warns that the boundaries
  are approximate; this project measures how much of each territory's total sits close
  to an edge and corrects nothing.
- It does not ask you to speak for the Commission, or for any utility, or to obtain
  anything that is not already public.

## Where the underlying material is

Everything cited above is committed in this repository and needs no access request.

- [ADR 0002, which published outlines are read as service territories](../adr/0002-which-published-outlines-are-service-territories.md),
  the rule itself and why it is the publisher's field rather than a judgment here.
- [ADR 0006, the inclusion rule measured against its alternatives](../adr/0006-the-inclusion-rule-is-measured-against-its-alternatives.md),
  what each reading of the field costs.
- [ADR 0010, an outline that holds no record is counted, not classified](../adr/0010-an-outline-that-holds-no-record-is-counted-not-classified.md),
  why the list above is 24 names long.
- [The glossary's entries for the six Type values](../GLOSSARY.md), each marked as the
  conventional reading rather than the publisher's definition.
- [The provenance record for both boundary layers](../../PROVENANCE.md), with the item
  identifiers, the retrieval date, the byte counts and the hashes.
- [The published report](../../published/REPORT.md) and the measurements it is rendered
  from, which is where every figure quoted here comes from and where a test holds this
  document to them.

This project is not affiliated with, endorsed by, or approved by CAL FIRE, the
California Energy Commission, or any electric utility, and a review of this packet does
not make a reviewer any of those things either.
