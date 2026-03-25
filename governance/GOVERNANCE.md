# SCM Open Source Governance Charter

**Effective Date:** 1st April 2026

**Organization:** Garudex Labs

**Licensing:** Apache License 2.0

> Disclaimer: This governance structure is currently operating under a provisional testing phase and will be formally finalized and ratified at a later date.

## ARTICLE I: PURPOSE AND JURISDICTION

**Section 1.01. Purpose.** 
This Governance Charter (the "Charter") establishes the operational, participatory, and administrative framework for the SCM project (the "Project"). SCM operates as a well-governed, open-source project managed by Garudex Labs for open-source development. The intent of this Charter is to provide a transparent, merit-based system for code contribution, review, role assignment, and dispute resolution.

**Section 1.02. Jurisdiction and Registry.** 
All governance matters, role assignments, and historical contribution records shall be documented and maintained within the official repository's contributor registry, specifically designated as the `contributors.yaml` file. This file shall serve as the sole canonical source of truth regarding contributor status and privileges.

## ARTICLE II: CONTRIBUTOR CLASSIFICATIONS AND PRIVILEGES

**Section 2.01. The Newbie Contributor.** 
The designation of Newbie Contributor is granted to individuals who have successfully achieved a minimum of one merged Pull Request (PR) or a verified documentation contribution. Individuals holding this role are granted fundamental privileges, including basic issue assignment and formal listing within the contributor registry. The primary responsibility of a Newbie Contributor is strict adherence to the Project’s contribution guidelines and testing standards. Once earned, this designation becomes a permanent historical record and shall not be revoked.

**Section 2.02. The Active Contributor.** 
The designation of Active Contributor is granted to individuals who have demonstrated consistent engagement, defined as executing five or more meaningful contributions within a rolling ninety-day period. Active Contributors are granted elevated privileges, including visibility into the Project roadmap and assignment to larger, complex tasks. In return, they are expected to assume ownership of specific issues and provide timely peer reviews.

**Section 2.03. The Core Contributor.** 
The designation of Core Contributor is reserved for individuals who have maintained ownership of at least one Project subsystem for a minimum of three months while demonstrating consistent, high-quality code contributions. Core Contributors possess PR review and merge rights within their domain and hold the authority to promote individuals to the Newbie and Active Contributor tiers. They bear the responsibility of enforcing code standards and actively mentoring junior contributors.

**Section 2.04. The Principal Contributor.** 
The designation of Principal Contributor is awarded to individuals demonstrating sustained, multi-quarter impact, deep technical ownership, and community leadership. Principal Contributors are authorized to assign all subordinate roles and are eligible for nomination to Maintainer status. They are entrusted with the long-term stewardship of the Project, including security audits, release management, and guiding the overall architectural vision.

## ARTICLE III: NOMINATION, PROMOTION, AND DEMOTION PROCEDURES

**Section 3.01. Promotion Mechanisms.** 
Role advancement within the Project is entirely peer-driven and merit-based. Candidates must be formally nominated via the official governance issue tracker by a contributor residing in the tier immediately senior to the candidate’s current tier. Nominations must include a written rationale citing the candidate's contribution history, key PRs, and measurable impact. Following a formal review by the nominating tier, approved promotions shall be recorded in the contributor registry and published in the Project release notes. Nominations for the Principal Contributor tier require exclusive review and approval by the existing SCM Maintainers.

**Section 3.02. Automated Activity Tracking and Inactivity Flags.** 
To ensure the contributor registry accurately reflects the active development community, an automated activity tracking protocol is enforced. Any contributor exhibiting zero recorded activity—defined as an absence of PRs, peer reviews, or governance comments—for a period of ninety consecutive days shall be automatically flagged as "Inactive" within the registry.

**Section 3.03. Demotion and Archival.** 
Should a contributor's inactivity extend to one hundred and eighty consecutive days, they shall be subject to a mandatory one-tier role demotion. At three hundred and sixty-five consecutive days of inactivity, the individual’s active role shall be archived, though their historical contributions will remain permanently logged. The SCM Maintainers reserve the right to override time-based demotions for Core and Principal Contributors under extenuating circumstances, provided a written rationale is documented. 

**Section 3.04. Reactivation.** 
An Inactive or demoted contributor may restore their active status and clear all inactivity flags immediately upon the submission and approval of a new contribution. Reinstatement to prior senior roles shall be evaluated in accordance with current promotion rules.

## ARTICLE IV: GOVERNANCE OPERATIONS AND AUTOMATION

**Section 4.01. Automated Governance Synchronization.** 
The Project utilizes a transparent, auditable automation workflow to support administrative functions. This system synchronizes GitHub activity daily and upon commits to the main branch, maintaining a global chronological log (`ledger.yaml`) and individual contributor histories.

**Section 4.02. Automation Oversight.** 
The automated system is authorized to process routine administrative tasks, including ninety-day inactivity flagging, automatic onboarding of Newbie Contributors upon their first merged PR, and parsing role-change commands executed within PR bodies. However, to ensure human oversight, all automated state changes shall be generated as Pull Requests requiring explicit approval and merging by an SCM Maintainer before taking effect.

## ARTICLE V: LEADERSHIP, OVERSIGHT, AND DISPUTE RESOLUTION

**Section 5.01. Maintainer Responsibilities.** 
SCM Maintainers are the chief custodians of the Project's operational health and strategic direction under the Garudex Labs umbrella. Maintainers are exclusively responsible for issue triage, the enforcement of label and merge policies, the appointment of Principal Contributors, and the evaluation of long-term stewardship candidates. 

**Section 5.02. Conflict Resolution and Appeals.** 
Disputes regarding code, architecture, or governance must first be documented in the governance tracker for mediation by the SCM Maintainers. Should a contributor face an adverse governance action (e.g., demotion or removal), they reserve the right to file a formal appeal. Upon receipt of an appeal, the Maintainers shall convene a review panel and render a binding decision within twenty-one calendar days.

**Section 5.03. Code of Conduct Enforcement.** 
All contributors and participants are legally bound by the Project’s Code of Conduct. The Maintainers reserve the absolute right to restrict privileges, issue demotions, or permanently ban individuals who breach these terms, prioritizing the safety and collaborative integrity of the open-source community.

## ARTICLE VI: AMENDMENTS AND RATIFICATION

**Section 6.01. Policy Modifications.** 
This Charter is maintained by the core engineering team and Garudex Labs. Proposed amendments to this Charter must be submitted via a Pull Request to the official repository. Substantive modifications mandate a minimum fourteen-day community comment period to ensure adequate public review.

**Section 6.02. Final Authority.** 
Following the mandated comment period, final ratification of any amendments rests exclusively with the SCM Maintainers. The Maintainers retain the authority to adopt, modify, or reject proposed changes to ensure the Project remains legally compliant, secure, and aligned with Garudex Labs' open-source objectives.