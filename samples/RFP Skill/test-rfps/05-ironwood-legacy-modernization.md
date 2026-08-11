# IRONWOOD MANUFACTURING — REQUEST FOR PROPOSAL

**RFP IW-2026-SHOPFLOOR: Replacement of the Shop Floor Control System**

| | |
| --- | --- |
| Issued | April 6, 2026 |
| Questions due | April 16, 2026 |
| Proposals due | May 6, 2026 |
| Anticipated award | May 27, 2026 |
| Anticipated start | June 15, 2026 |

---

## 1. Background

Ironwood Manufacturing produces precision metal components from three plants in
Indiana, running two shifts, roughly 640 production staff.

Production scheduling, work-order tracking, and quality holds run on an in-house
system built in Visual Basic 6 against a SQL Server 2008 database, first
deployed in 2003 and extended continuously since. It works. That is the problem:
it is load-bearing, undocumented, and the two people who understood it have both
retired. Nobody currently employed can safely change it, and the operating system
it depends on is out of support.

**We cannot stop production to replace it.** The plants run continuously; any
approach requiring a hard cutover across all three sites simultaneously will not
be considered.

## 2. What we are asking for

We are deliberately not prescribing a solution. We want a vendor to assess what
we have, propose an approach that manages the risk of replacing a system nobody
fully understands, and then execute it.

Vendors should be explicit about how they would discover and preserve business
rules that exist only in the current code.

## 3. Requirements

R1. Assess the existing application and produce a modernization roadmap.
R2. Preserve every business rule currently enforced by the legacy system, and
    document each one as it is carried forward.
R3. Migrate 22 years of historical production and quality data, with validation
    and reconciliation against the source.
R4. Move to a supported, cloud-hosted platform.
R5. Transition incrementally. Parallel running is expected; a plant-by-plant or
    function-by-function sequence is acceptable.
R6. Integrate with our existing Epicor ERP.
R7. Integrate with the plant-floor data collection terminals (currently serial,
    being replaced with networked units during 2026).
R8. Provide a rollback plan for each cutover step.
R9. Staff authentication via our existing Active Directory.
R10. Reduce ongoing maintenance cost and single-person dependency.

## 4. Constraints

- No production downtime beyond the existing Sunday 02:00–06:00 maintenance window.
- The legacy system must remain authoritative until each function is proven in the
  new platform.
- Source code for the legacy system is available. Documentation is not — there is
  none beyond code comments.

## 5. Budget

Ironwood has allocated **$700,000 to $1,400,000** across fiscal 2026–2027.

## 6. Evaluation criteria

| Criterion | Weight |
| --- | ---: |
| Technical approach, especially transition and rollback | 35 |
| Relevant modernization experience | 25 |
| Cost and value | 20 |
| Project team | 10 |
| Timeline | 10 |

## 7. Submission

Submit to Ms. Carla Denton, Director of Operations, quoting **RFP
IW-2026-SHOPFLOOR**.
