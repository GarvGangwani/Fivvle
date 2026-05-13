"""Eval set ideas for the research engine.

10 founder ideas covering 8 domains. These are fixed inputs used to evaluate
research engine prompt quality. Each idea is a realistic founder submission
paired with a hand-populated RefinedIdea — the exact input the research engine
receives in eval runs, so we don't re-spend refinement tokens per eval run.

Ideas 1–5 (slack-hr-bot through newsletter-affiliate) are the raw texts from
backend/scripts/try_refinement.py, with RefinedIdea fields populated to match
what the production refinement service produces for those inputs.

Ideas 6–10 cover domains underrepresented in the initial script: social-impact,
fintech, health-tech, a supply-hard marketplace edge case, and a deliberately
vague idea that tests whether the research engine flags "too vague to research"
rather than fabricating findings.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.refinement import RefinedIdea

# Domains allowed in the eval set — match the taxonomy used for research engine
# prompt routing and coverage analysis.
ALLOWED_DOMAINS: frozenset[str] = frozenset(
    {
        "b2b-saas",
        "consumer",
        "marketplace",
        "dev-tool",
        "creator-economy",
        "social-impact",
        "fintech",
        "health-tech",
    }
)


class EvalIdea(BaseModel):
    """A single founder idea in the eval set."""

    id: str  # short slug, e.g. "slack-hr-bot"
    domain: str  # one of ALLOWED_DOMAINS
    raw_idea: str  # 2-5 sentences as a founder would actually type it (50-2000 chars)
    refined_idea: RefinedIdea  # direct input to research engine in eval runs
    notes: str  # 1-2 sentences on why this idea is in the eval set


# ---------------------------------------------------------------------------
# IDEA 1 — B2B SaaS: Slack policy / HR bot
# Source: scripts/try_refinement.py idea #1, verbatim raw text.
# RefinedIdea fields match production refinement output for this input.
# ---------------------------------------------------------------------------
_IDEA_SLACK_HR_BOT = EvalIdea(
    id="slack-hr-bot",
    domain="b2b-saas",
    raw_idea=(
        "We're building a tool for operations managers at mid-sized companies (50-500 employees)\n"
        "who are drowning in ad-hoc Slack messages asking 'what's the policy on X?'. Every week\n"
        "there are 20-30 questions like 'can I expense this?', 'what's the PTO carryover rule?',\n"
        "'do we have a parental leave policy?' that should have answers in the handbook but the\n"
        "handbook is a 200-page Google Doc nobody reads. Our idea is an AI that sits in Slack,\n"
        "watches for those questions, and instantly drafts an answer from the actual company\n"
        "policy documents — so ops managers don't have to manually answer the same questions\n"
        "every week and employees get faster answers."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "An AI Slack bot that answers employee HR and policy questions by searching your "
            "company's actual documents, so ops managers stop fielding the same questions weekly."
        ),
        target_audience=(
            "Operations managers at Series A–C tech companies with 50–500 employees who personally "
            "spend 2–3 hours per week answering Slack messages about PTO rules, expense policies, "
            "and parental leave buried in a 200-page Google Doc nobody opens."
        ),
        value_proposition=(
            "Cuts the 2–3 hour weekly ops-manager burden of answering repeat policy questions in "
            "Slack — employees get instant answers from the actual handbook without waiting for a "
            "human to find the right page in a 200-page document."
        ),
        risks=[
            "Are 50–500 person companies already using Guru, Notion AI, or Confluence Q&A "
            "to answer policy questions, making a dedicated Slack bot redundant?",
            "Do HR and legal teams have compliance concerns about an AI bot citing PTO or "
            "leave policies, creating liability when the bot misreads an outdated document?",
            "Is handbook staleness — not question routing — the real blocker, so the bot "
            "gives wrong answers unless someone continuously maintains the source documents?",
            "Do operations managers at Series A–B companies have budget authority for new "
            "software, or does every purchase require a 60-day procurement process?",
        ],
        headline="Policy answers in Slack — without tagging ops every time",
        subheadline=(
            "Connect your handbook. The bot handles 'what's the PTO rule?' so your ops team "
            "stops answering it for the 30th time this month."
        ),
        cta_text="Join the waitlist",
    ),
    notes=(
        "Tests whether the research engine identifies Guru and Notion AI as direct competitors "
        "and surfaces the handbook-staleness problem that undermines the core value proposition."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 2 — Consumer: Fitness accountability + loss aversion app
# Source: scripts/try_refinement.py idea #2, verbatim raw text.
# ---------------------------------------------------------------------------
_IDEA_FITNESS_ACCOUNTABILITY = EvalIdea(
    id="fitness-accountability",
    domain="consumer",
    raw_idea=(
        "I want to make a fitness app specifically for people who keep starting and stopping\n"
        "workout plans. The existing apps are full of features but nobody finishes anything.\n"
        "My idea is super simple — you pick one habit per week, find a partner on the app who\n"
        "has the same goal, and you both have to 'check in' daily with a photo. If your partner\n"
        "doesn't check in by 9pm, you both get charged $5 to a charity you chose at signup.\n"
        "Loss aversion and social accountability combined. I've talked to 30 people and most of\n"
        "them have tried at least 3 fitness apps and quit all of them."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "A two-person fitness accountability app where you pick one habit per week, check in "
            "daily with a photo, and both partners get charged $5 to charity for any missed day."
        ),
        target_audience=(
            "Adults in their 20s–30s who have downloaded 3+ fitness apps and quit all of them — "
            "specifically people who say no external consequence makes quitting feel costly and "
            "that solo apps can't replicate the guilt of letting someone else down."
        ),
        value_proposition=(
            "Converts the abstract intention to be consistent into a daily social contract with "
            "real financial stakes — making skipping cost something concrete rather than just "
            "another streak reset in an app you eventually mute."
        ),
        risks=[
            "Did Pact (GymPact) and StickK users actually pay when charged, or did most cancel "
            "before charges hit — making the financial penalty mechanic ineffective in practice?",
            "Is there a cold-start partner-matching problem: can the app match users on compatible "
            "goals fast enough that long waits don't kill motivation before a match is found?",
            "Does the one-habit-per-week constraint reduce complexity enough to prevent churn, "
            "or do users still quit just as fast when life disrupts a single-streak app?",
            "Are there payment processing or consumer protection concerns with automatically "
            "charging users for missed check-ins under strict auto-charge rules by jurisdiction?",
        ],
        headline="Miss your workout? You and your partner each owe $5 to charity.",
        subheadline=(
            "Pick one habit per week. Find a partner with the same goal. "
            "Check in daily with a photo — or you both pay."
        ),
        cta_text="Find my partner",
    ),
    notes=(
        "Tests whether the engine surfaces Pact/GymPact and StickK as direct precedents "
        "with documented failure modes, and flags the cold-start matching problem."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 3 — Marketplace: Short-form video editor marketplace
# Source: scripts/try_refinement.py idea #3, verbatim raw text.
# ---------------------------------------------------------------------------
_IDEA_VIDEO_EDITOR_MARKETPLACE = EvalIdea(
    id="video-editor-marketplace",
    domain="marketplace",
    raw_idea=(
        "There's no good marketplace for short-form video editing freelancers. Fiverr and Upwork\n"
        "are messy, over-indexed on web developers and logo designers, and the quality varies\n"
        "wildly. I want to build a curated marketplace just for video editors who specialize in\n"
        "social content (TikTok, Reels, YouTube Shorts). Brands and creators post a brief,\n"
        "editors apply with a portfolio of short-form work, and we vet every editor before they\n"
        "join. The model is project-based, not hourly, and we handle contracts and payments.\n"
        "I've seen brand teams waste weeks going through 50 Upwork applications to find someone\n"
        "who actually knows how to edit for social."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "A curated marketplace for short-form video editors specializing in TikTok, Reels, "
            "and YouTube Shorts — brands post briefs, vetted editors apply, project-based pricing."
        ),
        target_audience=(
            "Brand marketing managers and social leads at DTC and mid-size consumer brands "
            "who have spent 2–4 weeks sorting Upwork or Fiverr applicants for an editor who "
            "actually understands TikTok pacing, hook structures, and platform-native formats."
        ),
        value_proposition=(
            "Cuts time-to-hire for a vetted short-form video editor from 2–4 weeks to 48 hours "
            "by pre-vetting every editor for social-content specialization and filtering out the "
            "generalist noise that makes Upwork searches so slow and unreliable."
        ),
        risks=[
            "Is supply already organized in Discord servers and LinkedIn communities where brands "
            "find editors directly — making a dedicated platform redundant for the quality segment?",
            "Do brand teams at the $500–3,000/project tier have the brief-writing skills to run a "
            "marketplace process, or do they prefer agency retainers that abstract away the work?",
            "Has the short-form video editing niche on Upwork improved enough in 2024–2025 with "
            "review filtering that the quality-signal problem is already partially solved?",
            "What minimum editor density per format (TikTok vs. Reels vs. Shorts) gives buyers "
            "meaningful choice without spreading supply too thin at launch?",
        ],
        headline="Hire a vetted short-form video editor in 48 hours",
        subheadline=(
            "Every editor on the platform specializes in TikTok, Reels, and YouTube Shorts — "
            "no generalists, no sifting through 50 applications."
        ),
        cta_text="Post a brief",
    ),
    notes=(
        "Tests whether the engine identifies Contra or Malt as curated freelance marketplace "
        "precedents and surfaces the supply-side cold-start problem specific to niche marketplaces."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 4 — Dev tool: Observability correlation / incident timeline
# Source: scripts/try_refinement.py idea #4, verbatim raw text.
# ---------------------------------------------------------------------------
_IDEA_OBSERVABILITY_TIMELINE = EvalIdea(
    id="observability-timeline",
    domain="dev-tool",
    raw_idea=(
        "I'm a backend engineer and my biggest daily frustration is that when a production bug\n"
        "happens I spend 30-60 minutes jumping between Datadog, Sentry, our Postgres logs, and\n"
        "Slack searching for context before I can even form a hypothesis. My idea is a tool that\n"
        "sits on top of your existing observability stack (doesn't replace anything) and when\n"
        "you paste in an error or incident ID, it automatically pulls the correlated logs,\n"
        "recent deploys, database slow queries, and any related Sentry issues from the same\n"
        "timeframe and puts them all in one scrollable timeline. Engineers already have all this\n"
        "data, they just can't see it together fast enough."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "A read-only correlation layer that pulls logs, deploys, slow queries, and Sentry "
            "issues from your existing stack into one timeline when you paste an incident ID."
        ),
        target_audience=(
            "Backend engineers at companies using 3+ observability tools who lose 30–60 minutes "
            "per production incident manually correlating signals across Datadog, Sentry, "
            "Postgres logs, and deploy history before they can form a debugging hypothesis."
        ),
        value_proposition=(
            "Collapses the 30–60 minute context-assembly phase of production debugging to under "
            "2 minutes by auto-correlating all observable signals from an incident ID into a "
            "single scrollable timeline — without replacing any existing tool."
        ),
        risks=[
            "Do platform teams at companies with mature stacks already have internal tooling for "
            "this correlation, making external products redundant for the segment most likely to pay?",
            "Is the real problem alert fatigue and signal-to-noise rather than timeline format — "
            "and does a better view actually reduce debugging time or just reformat the noise?",
            "What is the integration maintenance burden given that Datadog, Sentry, and GitHub "
            "APIs evolve independently — is connector upkeep the real product moat risk?",
            "Do SOC 2 and GDPR data residency policies prevent infrastructure teams from sending "
            "log data to a third-party service, even one positioned as read-only?",
        ],
        headline="One timeline. Every signal from the incident.",
        subheadline=(
            "Paste an error or incident ID — get correlated logs, deploys, slow queries, "
            "and Sentry issues from the same timeframe in one view."
        ),
        cta_text="Connect your stack",
    ),
    notes=(
        "Tests whether the engine identifies Incident.io, Rootly, and Grafana Incident as "
        "existing correlation tools and surfaces the data-residency concern as a sales blocker."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 5 — Creator economy: Newsletter affiliate matching platform
# Source: scripts/try_refinement.py idea #5, verbatim raw text.
# ---------------------------------------------------------------------------
_IDEA_NEWSLETTER_AFFILIATE = EvalIdea(
    id="newsletter-affiliate",
    domain="creator-economy",
    raw_idea=(
        "I write a weekly newsletter about personal finance for people in their 30s and I have\n"
        "about 8,000 subscribers but I'm only making money from one sponsor per issue. The\n"
        "problem is sponsorships are hard to sell, require minimum audience sizes most small\n"
        "newsletters don't have, and I'm leaving money on the table because I know my readers\n"
        "trust my recommendations. My idea is a platform that lets newsletter writers like me\n"
        "monetize through 'reader-matched affiliate deals' — the platform knows what financial\n"
        "products my readers have clicked on before and surfaces relevant affiliate partnerships\n"
        "I can include in my issues as genuine recommendations, not banner ads. Pay-per-click\n"
        "revenue that doesn't require a sales relationship."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "A platform that surfaces reader-matched affiliate deals for niche newsletter writers "
            "based on audience click history — per-click revenue without selling sponsorships."
        ),
        target_audience=(
            "Newsletter writers with 1,000–20,000 subscribers in a specific niche (personal "
            "finance, health, productivity) earning under $500/month from their list because "
            "they lack the audience size required for direct sponsorship deals."
        ),
        value_proposition=(
            "Adds $200–1,500/month in affiliate revenue for niche newsletter writers without "
            "requiring them to sell sponsorships or maintain advertiser relationships — deals "
            "are matched automatically to what the audience already clicks."
        ),
        risks=[
            "Do Beehiiv Boosts, Substack's partner program, or Kit's commerce features already "
            "solve affiliate matching for newsletters under 20k subscribers, making a standalone "
            "platform redundant?",
            "Is reader-behavior tracking feasible given that Apple MPP and Gmail caching block "
            "open pixels — undermining the 'matched to what they click' core mechanic?",
            "Do financial product affiliate programs (brokerages, credit cards) allow newsletter "
            "placements, and are payout rates high enough to generate real revenue at sub-20k lists?",
            "Does the 'genuine recommendation' framing conflict with FTC disclosure requirements "
            "in ways that create legal risk for writers whose brand depends on reader trust?",
        ],
        headline="Earn from your newsletter without selling a single sponsorship",
        subheadline=(
            "The platform matches affiliate deals to what your readers already click — "
            "so every recommendation fits your audience."
        ),
        cta_text="See what you'd earn",
    ),
    notes=(
        "Tests whether the engine identifies Beehiiv Boosts and Apple MPP as the two existential "
        "threats to this model and surfaces FTC disclosure requirements as a trust risk."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 6 — Social impact: Immigration deadline tracker for visa holders
# NEW idea covering the social-impact domain.
# ---------------------------------------------------------------------------
_IDEA_VISA_DEADLINE_TRACKER = EvalIdea(
    id="visa-deadline-tracker",
    domain="social-impact",
    raw_idea=(
        "I've been on an H-1B for 4 years and the thing that stresses me out most isn't the "
        "visa itself, it's all the deadlines around it — when to file for extension, when my "
        "I-94 expires vs. when my visa stamp expires, when the lottery opens, when I need to "
        "update USCIS for an address change. I missed one deadline last year because I thought "
        "my lawyer was tracking it and she thought I was. It cost me $1,500 in emergency "
        "filing fees. I want to build something for H-1B and other work visa holders that "
        "tracks all their personal immigration deadlines, reminds them 90/60/30 days out, "
        "and explains in plain English what each deadline actually means and what happens if "
        "you miss it. Not legal advice, just a personal calendar for your immigration timeline."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "A personal deadline tracker for US work visa holders (H-1B, L-1, OPT) that maps "
            "their immigration timeline, sends 90/60/30-day reminders, and explains each "
            "deadline in plain English."
        ),
        target_audience=(
            "H-1B holders 2–4 years into their visa cycle at mid-size tech companies without "
            "dedicated immigration coordinators — managing their own deadlines alongside an "
            "employer immigration attorney with no personal source of truth for which deadlines "
            "they individually own vs. which their employer owns."
        ),
        value_proposition=(
            "Eliminates missed immigration deadlines by giving visa holders a personal dashboard "
            "that separates individual-owned from employer-owned deadlines and sends tiered alerts "
            "— turning a $1,500 emergency filing risk into a routine calendar event."
        ),
        risks=[
            "Do larger employers' H-1B holders already get deadline tracking through Fragomen "
            "or Envoy Global retainer portals — leaving only unrepresented holders as real users?",
            "Do USCIS deadline rules change frequently enough that maintaining accurate logic "
            "requires ongoing attorney review — making the product expensive to keep current?",
            "Does 'not legal advice' positioning block marketing through immigration attorneys "
            "and HR departments, the most cost-effective channels for reaching H-1B holders?",
            "Do unrepresented H-1B holders — the highest-need segment — have the lowest "
            "willingness to pay for immigration tools since their employer isn't covering the cost?",
        ],
        headline="Never miss an immigration deadline again",
        subheadline=(
            "Your visa timeline, your reminders, in plain English — built for H-1B, L-1, "
            "and OPT holders managing their own immigration calendar."
        ),
        cta_text="Track my visa deadlines",
    ),
    notes=(
        "Social-impact domain; tests whether the engine identifies immigration firm client "
        "portals as a competitor and surfaces the UPL (unauthorized practice of law) regulatory "
        "risk specific to this category."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 7 — Fintech: Automated tax-loss harvesting for solo founders
# NEW idea covering the fintech domain.
# ---------------------------------------------------------------------------
_IDEA_TAX_LOSS_HARVESTING = EvalIdea(
    id="tax-loss-harvesting",
    domain="fintech",
    raw_idea=(
        "I'm a solo founder who paid $18,000 in capital gains tax last year on some early "
        "startup equity I sold. My accountant told me afterward that I could have offset a lot "
        "of it with tax-loss harvesting from my brokerage account if I'd done it before year-end. "
        "The problem is I didn't know what positions to sell, when to do it, or how to avoid the "
        "wash sale rule. Big wealth managers automate this for their clients but you need like "
        "$250k minimum. I want to build something that connects to your brokerage, looks at your "
        "unrealized losses vs. your estimated capital gains for the year, and tells you exactly "
        "which positions to sell and when — automated, no advisor required. Target user is "
        "solo founders and early employees who had a liquidity event and now have a mixed "
        "brokerage account they don't know how to manage."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "Automated tax-loss harvesting for individual investors: connects to your brokerage, "
            "identifies sell candidates against YTD capital gains, and avoids wash-sale "
            "violations — no wealth manager required."
        ),
        target_audience=(
            "Solo founders, angel investors, and early startup employees with $50k–$500k in "
            "taxable brokerage accounts who realized capital gains from an equity event but "
            "lack access to the automated tax optimization that private wealth managers provide "
            "at $250k+ minimums."
        ),
        value_proposition=(
            "Recovers $2,000–$15,000 in annual tax liability for investors with mixed portfolios "
            "by automating the harvest analysis and timing that currently requires a private "
            "wealth advisor or significant DIY tax expertise to execute correctly before year-end."
        ),
        risks=[
            "Do Betterment, Wealthfront, and Fidelity already provide automated harvesting at "
            "$50k–$500k AUM — and if so, is the gap only for taxable accounts outside those "
            "platforms?",
            "Does a tool making specific sell recommendations trigger SEC RIA registration "
            "requirements that would make MVP launch impossible without expensive legal "
            "infrastructure?",
            "Is the harvest window so concentrated (October–December) that users engage only "
            "6–8 weeks per year, creating a severe retention and subscription model problem?",
            "Does Plaid provide real-time unrealized gain/loss data across major brokerages "
            "reliably enough to make accurate recommendations without requiring CSV uploads?",
        ],
        headline="Harvest tax losses before December — without a wealth manager",
        subheadline=(
            "Connect your brokerage, see which positions to sell against your capital gains, "
            "and avoid the wash sale rule automatically."
        ),
        cta_text="Connect my brokerage",
    ),
    notes=(
        "Fintech domain with regulatory complexity; tests whether the engine identifies SEC RIA "
        "registration as a launch blocker and surfaces Betterment/Wealthfront as the primary "
        "competitive threat."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 8 — Health tech: Medication adherence tracker for elderly patients
# NEW idea covering the health-tech domain.
# ---------------------------------------------------------------------------
_IDEA_MEDICATION_ADHERENCE = EvalIdea(
    id="medication-adherence",
    domain="health-tech",
    raw_idea=(
        "My mom is 74 and lives alone. She takes 7 medications and has missed doses at least a "
        "dozen times this year that I know about. The existing pill reminder apps are either too "
        "complicated for her to set up, require her to enter all her own medications, or are "
        "basically just alarms with no tracking. What I want is something where I — her daughter "
        "— can set everything up on my end, input her medications and schedule, and then she just "
        "gets simple nudges on her phone that she can tap to confirm she took the pill. I get a "
        "quiet alert if she hasn't confirmed by a certain time. Not a medical device, not "
        "Medicare-billed, just a simple family coordination layer for medication reminders. "
        "The person who cares about adherence is the adult child, not always the patient."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "A medication reminder app where an adult child configures the schedule remotely, "
            "the elderly parent gets one-tap confirmations, and family members receive quiet "
            "alerts for missed doses."
        ),
        target_audience=(
            "Adult children (ages 40–60) managing medication adherence for an elderly parent "
            "living independently — specifically those whose parent resists complicated technology "
            "but whose doctor has flagged missed doses as a health risk requiring family oversight."
        ),
        value_proposition=(
            "Eliminates the daily 'did you take your pill?' call by giving family caregivers a "
            "simple remote dashboard to configure medication reminders and receive missed-dose "
            "alerts, while keeping the patient's interaction to a single tap on their phone."
        ),
        risks=[
            "Does Medisafe support a caregiver-configuration workflow where an adult child sets "
            "up the schedule remotely, or is it patient-first in a way that breaks for elderly "
            "users who resist technology?",
            "Is the elderly patient's willingness to tap a daily confirmation the primary blocker "
            "— making a physical pill dispenser (Hero, Lively) a better fit than a phone app?",
            "Does 'not a medical device' positioning block marketing through pharmacies and "
            "geriatric practices — the most cost-effective channels for reaching caregivers?",
            "Does usage peak at setup and fade as families find routines, or is medication "
            "adherence persistent enough that daily engagement justifies subscription pricing?",
        ],
        headline="Set up your parent's medication reminders from your phone",
        subheadline=(
            "You configure the schedule, they tap to confirm, you get alerted if they miss a "
            "dose — without the daily 'did you take your pill?' call."
        ),
        cta_text="Set up for my parent",
    ),
    notes=(
        "Health-tech domain testing whether the engine distinguishes the caregiver-first vs. "
        "patient-first configuration gap and surfaces Hero/Lively smart dispensers as a "
        "physical-product alternative that may outperform an app in this demographic."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 9 — Marketplace (supply-hard edge case): Independent auto mechanic booking
# NEW idea covering a marketplace where supply is the hard side.
# ---------------------------------------------------------------------------
_IDEA_MECHANIC_MARKETPLACE = EvalIdea(
    id="mechanic-marketplace",
    domain="marketplace",
    raw_idea=(
        "I want to build a marketplace for independent auto mechanics — certified ones, not the "
        "Jiffy Lube franchise type. Finding a trustworthy mechanic when you move to a new city "
        "is genuinely hard. Yelp reviews are gamed, dealerships overcharge, and word-of-mouth "
        "only works if you know people. The mechanics I've talked to say they're already full — "
        "their regulars keep them busy — but they lose customers every year when people move "
        "away. I want a platform where mechanics list their availability and specialties, "
        "customers book directly, mechanics control their pricing, and we take a small booking "
        "fee. The supply is the hard side here — good mechanics don't need another lead-gen "
        "platform and I need to figure out the right incentive to get them to list."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "A booking marketplace for vetted independent auto mechanics — ASE-verified listings "
            "with real availability, mechanic-set pricing, and a booking fee model that doesn't "
            "require mechanics to advertise."
        ),
        target_audience=(
            "Car owners who have recently moved to a new city or lost their trusted mechanic and "
            "face a repair need — specifically those already burned by a dealership overcharge or "
            "a Yelp-reviewed shop that turned out to be low quality."
        ),
        value_proposition=(
            "Replaces the unreliable Yelp-and-hope workflow for finding a trustworthy independent "
            "mechanic by providing verified ASE certifications, real booking availability, and "
            "mechanic-set pricing — so customers stop overpaying at dealerships by default."
        ),
        risks=[
            "Do mechanics who are already at capacity have any incentive to join a platform that "
            "adds scheduling overhead without solving their real problem of slow-season cash flow?",
            "Have RepairPal and YourMechanic (now Wrench) validated or invalidated this model — "
            "and if they pivoted, what specifically broke the mechanic-supply acquisition strategy?",
            "Do mechanics take customers off-platform after the first job to avoid booking fees "
            "— and does this off-platform leakage structurally undermine the marketplace model?",
            "What minimum mechanic density per metro area is needed for booking availability to "
            "feel meaningfully better than a dealership appointment queue?",
        ],
        headline="Find a trusted independent mechanic in your city — and actually book them",
        subheadline=(
            "Verified ASE certifications, real availability, mechanic-set prices. "
            "No dealership markups, no Yelp lottery."
        ),
        cta_text="Find a mechanic",
    ),
    notes=(
        "Supply-hard marketplace edge case; tests whether the engine identifies RepairPal and "
        "YourMechanic as failed/pivoted precedents and surfaces off-platform leakage risk "
        "specific to service marketplaces with high-trust repeat relationships."
    ),
)


# ---------------------------------------------------------------------------
# IDEA 10 — Deliberately vague: "AI productivity app"
# NEW idea testing the honesty criterion — research engine should flag
# "this idea is too vague to research" rather than fabricating findings.
# ---------------------------------------------------------------------------
_IDEA_VAGUE_PRODUCTIVITY = EvalIdea(
    id="vague-ai-productivity",
    domain="b2b-saas",
    raw_idea=(
        "I want to build an app for productivity that uses AI. There's a huge market for "
        "productivity tools and AI makes everything better now. I think this could be really "
        "big if we get the right features. We could help people do their work faster and I "
        "have some ideas about what features would be useful."
    ),
    refined_idea=RefinedIdea(
        refined_one_liner=(
            "An AI-powered productivity app for knowledge workers — the specific use case, "
            "workflow, and differentiator are not yet defined in the founder's concept."
        ),
        target_audience=(
            "Knowledge workers who feel unproductive — role, company size, specific workflow "
            "bottleneck, and nature of the productivity gap are all undefined in the current "
            "concept."
        ),
        value_proposition=(
            "Helps users complete work tasks faster using AI assistance — the specific tasks "
            "targeted, measurable time savings, and mechanism of improvement are not specified "
            "in the founder's submission, making the value proposition unverifiable."
        ),
        risks=[
            "Without a defined use case, who is the actual target customer and what specific "
            "workflow does this replace — is this idea researchable at all in current form?",
            "What distinguishes this from Notion AI, Microsoft Copilot, and Google Workspace AI "
            "given no specific differentiation is described by the founder?",
            "Is the concept specific enough for the research engine to return actionable findings "
            "— or does it need a sharper problem statement before any data would be meaningful?",
        ],
        headline="Work faster with AI",
        subheadline=(
            "An AI productivity tool for knowledge workers — specific use case and target "
            "workflow to be defined."
        ),
        cta_text="Get early access",
    ),
    notes=(
        "Deliberately vague idea that tests the honesty criterion: a good research engine "
        "should explicitly flag that the idea is too vague to research meaningfully rather "
        "than fabricating competitors or market sizes for an undefined product."
    ),
)


# ---------------------------------------------------------------------------
# Public list — all 10 ideas in domain-balanced order
# ---------------------------------------------------------------------------
EVAL_IDEAS: list[EvalIdea] = [
    _IDEA_SLACK_HR_BOT,
    _IDEA_FITNESS_ACCOUNTABILITY,
    _IDEA_VIDEO_EDITOR_MARKETPLACE,
    _IDEA_OBSERVABILITY_TIMELINE,
    _IDEA_NEWSLETTER_AFFILIATE,
    _IDEA_VISA_DEADLINE_TRACKER,
    _IDEA_TAX_LOSS_HARVESTING,
    _IDEA_MEDICATION_ADHERENCE,
    _IDEA_MECHANIC_MARKETPLACE,
    _IDEA_VAGUE_PRODUCTIVITY,
]
