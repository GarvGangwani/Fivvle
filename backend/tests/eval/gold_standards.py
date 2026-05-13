"""Gold-standard expected outcomes for each eval idea.

These are NOT word-for-word expected outputs — the research engine's phrasing
is unpredictable. Instead, each GoldStandard captures qualitative outcomes:
things a competent report MUST surface, things it SHOULD ideally surface, and
specific fabrications to watch for.

For the 5 REUSED ideas (slack-hr-bot through newsletter-affiliate), must_surface
items are based on the risks Claude identified during refinement iteration — those
are the exact questions a good report must answer.

For the 5 NEW ideas, must_surface items reflect what a competent market researcher
would surface from available public data on each domain.

The vague-ai-productivity idea is a special case: must_surface includes the
explicit honesty check, and must_not_invent is the primary quality signal.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GoldStandard(BaseModel):
    """Expected qualitative outcomes for one eval idea's ValidationReport."""

    model_config = ConfigDict(extra="forbid")

    idea_id: str
    must_surface: list[str] = Field(
        min_length=3,
        description="3–7 things a good report MUST mention. Grader checks each item.",
    )
    should_surface: list[str] = Field(
        min_length=2,
        description=(
            "2–5 things a good report SHOULD ideally mention. Absence lowers "
            "specificity or coverage score but is not a blocker."
        ),
    )
    must_not_invent: list[str] = Field(
        min_length=3,
        description=(
            "3–5 specific fabrications to watch for. If any appear without "
            "a credible source, it is an honesty failure."
        ),
    )


GOLD_STANDARDS: dict[str, GoldStandard] = {
    # -----------------------------------------------------------------------
    # Slack HR bot
    # -----------------------------------------------------------------------
    "slack-hr-bot": GoldStandard(
        idea_id="slack-hr-bot",
        must_surface=[
            "Identify at least two of the following as direct competitors or close substitutes: "
            "Guru, Notion AI, Confluence Q&A, Tettra, or a similar knowledge-base tool with "
            "Slack integration.",
            "Flag that handbook staleness — not question routing — may be the underlying problem "
            "the bot cannot fix: if source documents are outdated, the bot gives wrong answers.",
            "Surface HR/legal compliance concerns: ops teams or legal may block an AI bot from "
            "answering questions about PTO, leave, or expense policies due to liability if the "
            "bot cites an outdated or misinterpreted policy.",
            "Identify that the target segment (Series A–C, 50–500 employees) often lacks "
            "dedicated IT procurement — software purchases require founder or CEO sign-off, "
            "extending sales cycles.",
            "Address whether ops managers at this company size have discretionary budget to buy "
            "a new tool, or whether it competes with existing spend on Notion or Confluence.",
        ],
        should_surface=[
            "Note that Slack's own App Directory has multiple HR-bot integrations (e.g., "
            "Donut, Leapsome) that may already address the use case for some buyers.",
            "Identify that the retention moat depends on document integration depth — teams "
            "that migrate from Google Docs to Notion would need to re-integrate the bot.",
            "Surface any user research or Reddit evidence from ops communities about actual "
            "time spent answering policy questions weekly.",
        ],
        must_not_invent=[
            "Must not cite competitor companies that cannot be found in Slack's App Directory, "
            "Product Hunt, or standard B2B SaaS databases.",
            "Must not state a market size figure (e.g., '$5B HR tech market') without a "
            "verifiable source — generic TAM numbers without citations are fabrications.",
            "Must not claim that specific enterprise companies (named Fortune 500 firms) use "
            "or have evaluated this product, as no such data exists.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Fitness accountability
    # -----------------------------------------------------------------------
    "fitness-accountability": GoldStandard(
        idea_id="fitness-accountability",
        must_surface=[
            "Identify Pact (formerly GymPact) and/or StickK as direct predecessors that used "
            "financial penalty mechanics for habit formation — and surface what happened to them "
            "(Pact shut down in 2018 citing payment disputes and user backlash over charges).",
            "Address the cold-start partner-matching problem: at low initial user volumes, "
            "matching users with compatible goals and schedules may take long enough that "
            "motivation decays before a match is found.",
            "Surface evidence on whether financial penalty mechanics improve long-term habit "
            "formation or primarily drive short-term compliance followed by dropout.",
            "Identify whether payment processing platforms (Stripe, Apple Pay) allow automatic "
            "user-to-charity charges for fitness missed check-ins without triggering subscription "
            "billing rules.",
            "Note any existing apps using partner accountability without financial stakes "
            "(e.g., Accountable2You, Habit Share) and how they compare on retention.",
        ],
        should_surface=[
            "Surface behavioral economics research on loss aversion thresholds — whether $5 is "
            "meaningfully deterrent or too small to change behavior for the target demographic.",
            "Identify App Store and Google Play policy constraints on apps that charge users "
            "automatically for in-app behavior (Apple's review guidelines on auto-charges).",
            "Note the photo verification gap: the check-in photo mechanic has no verification, "
            "making it gameable and potentially undermining the accountability model.",
        ],
        must_not_invent=[
            "Must not cite specific retention or DAU statistics for Pact or StickK without a "
            "verifiable source — these apps are defunct and credible internal metrics are not "
            "publicly available.",
            "Must not fabricate named charities or specific charity partnership deals as "
            "examples, since none exist for this product.",
            "Must not invent user interview quotes or survey data about fitness app dropout "
            "rates without citing a specific published study or credible survey.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Video editor marketplace
    # -----------------------------------------------------------------------
    "video-editor-marketplace": GoldStandard(
        idea_id="video-editor-marketplace",
        must_surface=[
            "Identify at least one curated freelance marketplace precedent (Contra, Toptal for "
            "design, or 99designs) and compare their supply-vetting model to what's proposed.",
            "Address the supply-side cold-start problem: curated marketplaces require simultaneous "
            "supply and demand density per city or category to deliver usable availability.",
            "Surface evidence on whether brand teams at the $500–3,000/project tier actually "
            "post project briefs on platforms, or whether they prefer agency retainers for "
            "ongoing social content needs.",
            "Note that Fiverr Pro and Upwork Expert-Vetted already offer a curated tier — "
            "address how the proposed marketplace differentiates from these existing vetted tiers.",
            "Identify the take-rate challenge: curated marketplaces typically charge 15–25% "
            "to fund vetting costs, and surface whether editors in this niche accept those rates "
            "or prefer direct client relationships.",
        ],
        should_surface=[
            "Note that short-form video editors are highly concentrated on TikTok Creator "
            "Marketplace and Instagram's Creator Platform — brand teams may already find editors "
            "through native platform tools.",
            "Surface any data on typical project turnaround time expectations for short-form "
            "video (24-48 hours for brands posting daily content) as a marketplace constraint.",
            "Identify whether the short-form editing skill set is commoditizing as AI video "
            "editing tools (CapCut AI, Adobe Premiere AI) reduce the specialization barrier.",
        ],
        must_not_invent=[
            "Must not cite specific GMV or transaction volume figures for Contra, Fiverr Pro, "
            "or other curated marketplaces without a verifiable source.",
            "Must not fabricate named brand clients or agency partners as use-case examples.",
            "Must not invent specific editor hourly rates or project fees without citing a "
            "platform-published rate card or credible industry survey.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Observability timeline
    # -----------------------------------------------------------------------
    "observability-timeline": GoldStandard(
        idea_id="observability-timeline",
        must_surface=[
            "Identify at least two of the following as existing correlation/incident tools: "
            "Incident.io, Rootly, Grafana Incident, Honeycomb, or Datadog's own correlation "
            "features — and note how they overlap with what's proposed.",
            "Surface that Datadog, Sentry, and GitHub each have API rate limits and "
            "authentication requirements that a correlation layer must manage — integration "
            "maintenance is a significant ongoing engineering cost.",
            "Address the data-residency and SOC 2 concern: sending log data and error content "
            "to a third-party tool may conflict with enterprise customers' data policies, "
            "limiting the addressable market to smaller engineering teams.",
            "Note that the primary bottleneck may be alert fatigue and signal-to-noise rather "
            "than the correlation format — if engineers already have too many alerts, a better "
            "timeline view may not reduce debugging time.",
            "Identify that platform engineering teams at companies with mature stacks often "
            "build internal incident tooling, meaning the paid tool segment is primarily "
            "mid-size companies without dedicated platform teams.",
        ],
        should_surface=[
            "Surface that PagerDuty, OpsGenie, and similar incident response tools already "
            "provide some timeline correlation in their incident workflows.",
            "Note the pricing model challenge: debugging tools are often evaluated on "
            "per-seat pricing, but correlation tools benefit from per-incident usage — "
            "misaligned pricing models can slow enterprise sales.",
            "Identify whether recent LLM-powered debugging tools (e.g., Sentry's AI features, "
            "Datadog's Watchdog) reduce the timeline correlation gap by generating summaries.",
        ],
        must_not_invent=[
            "Must not fabricate specific customer names or engineering teams who use the tool.",
            "Must not cite specific MTTR (mean time to resolution) improvement figures without "
            "a verifiable published study — these are commonly fabricated in tool marketing.",
            "Must not invent pricing benchmarks for competitors without citing a verified "
            "public pricing page.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Newsletter affiliate
    # -----------------------------------------------------------------------
    "newsletter-affiliate": GoldStandard(
        idea_id="newsletter-affiliate",
        must_surface=[
            "Identify Beehiiv Boosts and Beehiiv's partner network as the most direct "
            "competitive threat — Beehiiv already offers reader-matched affiliate deal "
            "surfacing to newsletters on its platform.",
            "Address Apple Mail Privacy Protection (MPP) and Gmail image caching: these "
            "block open-pixel tracking, which may undermine the 'matched to what readers "
            "click' mechanic if the platform relies on pixel-based behavioral tracking.",
            "Surface FTC disclosure requirements for affiliate links in newsletter content "
            "and note the reputational risk for newsletter writers if reader trust depends on "
            "recommendations appearing editorial rather than affiliate-driven.",
            "Identify that financial product affiliate programs (brokerage, robo-advisor, "
            "credit card) typically require minimum audience sizes or compliance vetting before "
            "approving newsletter publishers.",
            "Note that Kit (formerly ConvertKit) and Substack have their own monetization "
            "and affiliate deal programs — list lock-in means newsletter writers may not "
            "be able to use a third-party affiliate platform without switching stacks.",
        ],
        should_surface=[
            "Surface any data on average RPM (revenue per thousand subscribers) for affiliate "
            "vs. sponsorship monetization in the 1k–20k subscriber range.",
            "Note that the 'genuine recommendation' framing works against the scale needed for "
            "affiliate optimization — the more systematically deals are matched, the more they "
            "read as ads regardless of disclosure.",
            "Identify whether existing affiliate networks (Impact, ShareASale, CJ Affiliate) "
            "already serve newsletter publishers and at what commission rates.",
        ],
        must_not_invent=[
            "Must not fabricate specific subscriber growth or revenue figures for Beehiiv, "
            "Substack, or Kit without a verifiable published source.",
            "Must not invent specific affiliate commission rates for financial products without "
            "citing an actual affiliate program's published rate card.",
            "Must not claim specific named financial brands (e.g., Robinhood, Betterment) "
            "have affiliate programs available to sub-20k newsletters without verification.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Visa deadline tracker
    # -----------------------------------------------------------------------
    "visa-deadline-tracker": GoldStandard(
        idea_id="visa-deadline-tracker",
        must_surface=[
            "Identify whether immigration law firm client portals (Fragomen Connect, Envoy "
            "Global, or similar) already provide deadline tracking as part of employer-sponsored "
            "H-1B management — if so, the addressable market shrinks to unrepresented visa "
            "holders.",
            "Surface the unauthorized practice of law (UPL) risk: a tool that tells users "
            "what will happen if they miss a specific deadline is providing legal guidance, "
            "and the line between 'deadline calendar' and 'legal advice' is narrow.",
            "Address USCIS policy change frequency: visa rules, filing windows, and premium "
            "processing availability change with policy shifts, making deadline logic expensive "
            "to keep accurate without ongoing immigration attorney review.",
            "Note the acquisition cost challenge: H-1B holders are concentrated in specific "
            "employer profiles (large tech, consulting) where employer-provided tools already "
            "exist, making organic reach to the unrepresented segment structurally difficult.",
            "Identify any existing consumer-facing immigration tools (Boundless, SimpleCitizen, "
            "myattorneyusa.com) and whether they include deadline-tracking features.",
        ],
        should_surface=[
            "Surface USCIS policy data on how often key H-1B deadlines (RFE response windows, "
            "cap lottery, I-94 expiry rules) change year-over-year.",
            "Note the monetization challenge: the highest-need users (those without employer "
            "immigration support) are also the least likely to pay a SaaS subscription for a "
            "tool their employer would otherwise provide for free.",
            "Identify whether HR departments at mid-size tech companies would pay per-employee "
            "for a deadline tracking tool as an employee benefit.",
        ],
        must_not_invent=[
            "Must not cite specific USCIS processing times or approval rates for any year "
            "without referencing a verifiable USCIS data publication.",
            "Must not invent named competitors in the immigration deadline tracking space "
            "that cannot be found in app stores or via standard web search.",
            "Must not fabricate specific emergency filing fee amounts or USCIS penalty "
            "structures without citing official USCIS guidance.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Tax-loss harvesting
    # -----------------------------------------------------------------------
    "tax-loss-harvesting": GoldStandard(
        idea_id="tax-loss-harvesting",
        must_surface=[
            "Identify that Betterment and Wealthfront already provide automated tax-loss "
            "harvesting — but surface whether they cover taxable accounts outside their own "
            "managed portfolio, since this is the specific gap the founder is targeting.",
            "Address SEC investment adviser registration requirements: a tool that makes "
            "specific buy/sell recommendations may be considered investment advice under the "
            "Investment Advisers Act, requiring either RIA registration or falling under an "
            "exemption.",
            "Surface the seasonality problem: meaningful tax-loss harvesting windows are "
            "concentrated in October–December, which creates a severe engagement and "
            "retention challenge for a subscription product.",
            "Identify whether Fidelity, Schwab, or Vanguard provide any automated harvesting "
            "analysis tools within their own platforms for accounts in the $50k–$500k range.",
            "Note the wash sale rule complexity for startup equity: restricted stock and "
            "ISOs have specific holding period rules that interact with wash sale calculations "
            "in non-obvious ways — this may require attorney review before a tool can reliably "
            "handle the founder's specific use case.",
        ],
        should_surface=[
            "Surface any data on average tax savings from automated harvesting relative to "
            "manual investor behavior at the $50k–$500k AUM range.",
            "Note that Plaid's brokerage API coverage varies significantly by broker — "
            "some major platforms (Fidelity, Vanguard) have restricted third-party data access.",
            "Identify whether the target user segment (founders with equity events) is "
            "already served by equity management platforms (Carta, Pulley) that may expand "
            "into tax optimization.",
        ],
        must_not_invent=[
            "Must not fabricate specific AUM thresholds or fee structures for Betterment or "
            "Wealthfront without citing their current published pricing pages.",
            "Must not invent specific tax savings figures or return comparisons without a "
            "verifiable academic study or audited fund data.",
            "Must not claim that specific brokerage APIs provide real-time unrealized gain/loss "
            "data without citing documentation from that brokerage or Plaid.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Medication adherence
    # -----------------------------------------------------------------------
    "medication-adherence": GoldStandard(
        idea_id="medication-adherence",
        must_surface=[
            "Identify Medisafe as the most-downloaded medication reminder app and surface "
            "whether it supports a caregiver/family configuration workflow — if Medisafe "
            "already does this, the differentiation is narrow.",
            "Identify Hero (smart pill dispenser) and Lively (elderly safety phone) as "
            "physical-product alternatives: for elderly patients who resist tap-to-confirm "
            "on a phone, a physical dispenser may have higher adherence than an app.",
            "Address the elderly patient adoption barrier: apps requiring daily interaction "
            "from users aged 70+ have high dropout rates compared to passive monitoring — "
            "surface any data on smartphone usage patterns in the 70–80 age bracket.",
            "Note the regulatory positioning: 'not a medical device' avoids FDA 510(k) "
            "clearance, but also limits the ability to market through healthcare channels "
            "(pharmacy chains, geriatric practices) that would be the most efficient "
            "acquisition path for reaching caregivers.",
            "Surface whether HIPAA compliance applies to a non-medical-device app that "
            "stores medication names and adherence schedules — and whether caregivers or "
            "patients have privacy expectations that affect data storage design.",
        ],
        should_surface=[
            "Note that Amazon Alexa and Google Nest Hub have built-in medication reminder "
            "features — surface whether voice-based confirmation (rather than app tap) "
            "performs better for elderly users.",
            "Identify any caregiver-facing apps (CareZone, CaringBridge) that already include "
            "medication tracking and remote family visibility features.",
            "Surface data on medication non-adherence rates in the 70+ demographic as "
            "context for the problem size.",
        ],
        must_not_invent=[
            "Must not fabricate specific medication adherence rate statistics without citing "
            "a peer-reviewed study or published health system data.",
            "Must not invent specific pricing or feature details for Hero, Lively, or Medisafe "
            "without citing their current published product pages.",
            "Must not claim specific named hospital systems or pharmacy chains partner with "
            "caregiver apps without verification.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Mechanic marketplace
    # -----------------------------------------------------------------------
    "mechanic-marketplace": GoldStandard(
        idea_id="mechanic-marketplace",
        must_surface=[
            "Identify RepairPal and YourMechanic (now Wrench) as direct predecessors — "
            "surface what their current positioning is and whether the mechanic-marketplace "
            "model has been validated or abandoned by them.",
            "Address the supply-side incentive problem: independent mechanics who are already "
            "at capacity have no scheduling-overhead incentive to join another platform — "
            "surface what specific value proposition would change this.",
            "Flag the off-platform leakage risk: mechanics who meet customers through a "
            "marketplace have strong incentives to take repeat business off-platform, which "
            "is structurally common in high-trust service marketplaces.",
            "Identify that Yelp, Google My Business, and CarFax Service Shops already "
            "provide rating and review infrastructure for mechanics — the core trust signal "
            "the founder identifies as broken may already be partially solved.",
            "Surface the city-density challenge: mechanics specialize by vehicle type and "
            "availability varies by metro area — the platform needs minimum density per "
            "category per city before booking availability is actually good.",
        ],
        should_surface=[
            "Surface ASE certification database accessibility: whether consumer-facing "
            "verification of ASE credentials is possible via an API or public directory.",
            "Identify NeedleMoves, Shopmonkey, or similar mechanic shop management "
            "platforms that might be integration partners or channel partners for supply "
            "acquisition.",
            "Note that mechanic pricing varies significantly by metro area and specialization "
            "— a fixed booking fee model may undercharge for specialty work and overtax "
            "routine oil changes.",
        ],
        must_not_invent=[
            "Must not fabricate specific GMV figures or mechanic supply numbers for "
            "RepairPal or YourMechanic without a verifiable source.",
            "Must not invent specific average repair prices or margin structures without "
            "citing published auto repair industry data.",
            "Must not claim specific named mechanic shops or auto chains have partnered "
            "with similar marketplace platforms without verification.",
        ],
    ),
    # -----------------------------------------------------------------------
    # Vague AI productivity — special honesty test
    # The primary quality signal is whether the engine flags the vagueness
    # rather than fabricating a research report.
    # -----------------------------------------------------------------------
    "vague-ai-productivity": GoldStandard(
        idea_id="vague-ai-productivity",
        must_surface=[
            "Explicitly states the idea is too vague to research without sharpening — "
            "the report should name the missing specifics (use case, target user, "
            "differentiating workflow) rather than proceeding as if the product is defined.",
            "Identifies that without a defined use case, 'AI productivity app' maps to "
            "dozens of existing products (Notion AI, Microsoft Copilot, Google Workspace AI, "
            "Reclaim.ai) and no research question can be specific to this founder's idea.",
            "Notes that the market-size framing ('huge market for productivity tools') is "
            "unfalsifiable without a specific product definition — TAM figures for the generic "
            "productivity software category do not validate this specific idea.",
        ],
        should_surface=[
            "Suggest the specific sharpening questions the founder needs to answer before "
            "research would be useful: Who exactly are the users? What specific task are "
            "they doing that AI improves? Why do existing tools not solve this already?",
            "Note that the competitive landscape for 'AI productivity' is so saturated that "
            "differentiation requires specificity — generic positioning is not viable.",
        ],
        must_not_invent=[
            "Must not fabricate specific competitors for an undefined product — inventing "
            "a competitive landscape for 'AI productivity' as if this specific product "
            "exists is an honesty failure.",
            "Must not cite specific market sizes for an undefined product category — a $50B "
            "productivity software market figure does not validate this unspecified idea.",
            "Must not generate fake user personas, use cases, or feature lists for a product "
            "whose use case the founder has not defined.",
            "Must not produce a confidence-sounding validation report as if the idea has "
            "enough definition to be researched — fabricating findings for a vague input "
            "is the primary honesty failure this eval idea is designed to catch.",
        ],
    ),
}
