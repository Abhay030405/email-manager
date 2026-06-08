# CampaignX — Extension Document
## Phase 1 Corrections + Phase 2 Advanced Additions
**Project: AI Multi-Agent Marketing Automation Platform**
**Author: Abhay Agarwal · MNNIT Allahabad**

---

> **How to read this document:**
> Phase 1 covers 6 corrections to the existing project — these transform it from a linear LLM pipeline into a genuinely agentic system. Phase 2 covers 6 new additions that expand the problem statement and make the platform enterprise-grade. Each addition is explained with the what, the why, how it works in practice, and a concrete real-world example showing the agent behavior in action.

---

# PHASE 1 — Corrections to the Existing System

## The Core Problem with CampaignX as Built

Before diving into additions, it is important to name the exact problem clearly. The current CampaignX architecture is a **sequential LLM pipeline disguised as a multi-agent system**. Here is what actually happens at runtime:

A user submits a campaign brief. The Brief Parser Agent receives it and makes one LLM call — it sends the brief text to GPT-4 with a prompt that says "extract the product, audience, goals, and CTA from this brief." GPT returns a JSON object. That JSON is passed to the Segmentation Agent, which makes one LLM call — it sends the customer list and asks GPT to "create meaningful segments." GPT returns segment descriptions. Those descriptions are passed to the Strategy Agent, which makes one LLM call. And so on down the chain.

LangGraph here is being used as an expensive `if-else` router. There is no real decision making happening at any node — every node does exactly one thing (call GPT) and the output deterministically flows to the next node. No agent ever decides to call a tool, check a result, loop back because something failed, or change its own behavior based on what it learned. GPT is doing everything including the work that should be done in code — clustering, scoring, analysis, validation.

The six additions below fix this systematically.

---

## Addition 1 — Real Tool Use for Every Agent

### What This Is

Every agent in Phase 1 gets a **tool belt** — a set of deterministic, code-based functions the agent can call to interact with the real world and observe results. The agent receives tool outputs, reasons about them, and decides what to do next. This is the definition of an agent: a system that perceives, reasons, and acts in a loop.

The critical distinction: tools are not LLM calls. Tools are deterministic functions — database queries, mathematical computations, API calls to external services, statistical tests. The LLM's job is to decide which tool to call, interpret the result, and decide what to do next. Python's job is to execute the tool and return the result faithfully.

### Why This Matters

Without tools, every agent is blind. It only knows what you put in the prompt. When the Content Generation Agent generates a subject line, it has no idea whether that subject line would land in the spam folder, whether the audience has seen similar subject lines three times this week, or whether it violates brand guidelines that are stored somewhere in your database. It just generates text based on its training data.

With tools, the same agent can check the spam score before returning the subject line, retrieve brand guidelines from the vector store to stay on-brand, check audience fatigue to avoid repeating patterns, and verify the subject line length fits the 60-character mobile preview limit. The agent's output is grounded in real system state, not hallucinated confidence.

### How It Works in Practice — Segmentation Agent

The Segmentation Agent currently asks GPT to "create three customer segments based on this data." In the tool-equipped version, the agent has access to four tools:

**Tool 1 — query_customer_database:** Executes a real MongoDB aggregation query. The agent can say "give me all customers in the 25–35 age range who made a purchase in the last 60 days and have an average order value above 1500 rupees." This is a real database query returning real rows, not GPT's guess at what those customers might look like.

**Tool 2 — compute_rfm_scores:** Takes a list of customer IDs and computes Recency, Frequency, Monetary scores in Python using actual transaction history. Recency is literally the number of days since the last purchase. Frequency is the count of transactions in the last 90 days. Monetary is the sum of all purchases. These are numbers computed from real data, not estimated.

**Tool 3 — run_clustering:** Takes the RFM scores as a feature matrix and runs sklearn's KMeans algorithm with k=3. Returns the cluster assignments, the centroid values for each cluster, and the silhouette score — a statistical measure of how well separated the clusters are. If the silhouette score is below 0.3, the clusters are not meaningful and the agent knows to try k=4 or k=2 instead.

**Tool 4 — validate_segment_size:** Takes a segment ID and checks whether it has enough members to be statistically useful for A/B testing. If a segment has only 40 people, sending them two email variants produces no statistically significant result. The tool returns a boolean and a recommendation — "minimum 200 members required for 95% confidence at 5% expected CTR."

**Real example of the agent loop:** The Segmentation Agent calls `compute_rfm_scores` on all 5,000 customers. It then calls `run_clustering` with k=3 and gets a silhouette score of 0.28 — too low. It reasons that the data might have a natural k=4 or k=5 structure and calls `run_clustering` again with k=4. The silhouette score comes back at 0.61 — much better. It then calls `validate_segment_size` on each of the four clusters and discovers that Cluster 3 has only 85 members. It merges Cluster 3 into the nearest cluster by centroid distance, validates again, and gets four segments all above 200 members. Only then does it call the LLM to generate human-readable names and descriptions for each segment. The LLM never touched the data — it only provided labels for what the math already determined.

### How It Works in Practice — Content Generation Agent

**Tool 1 — retrieve_brand_guidelines:** Queries the pgvector store with the campaign brief as the search query. Returns the top 5 most relevant chunks from the brand guidelines document — tone of voice, forbidden words, approved CTAs, color palette descriptions for HTML emails, signature format. The agent reads these before generating any content.

**Tool 2 — check_spam_score:** Sends the generated subject line and email body to a SpamAssassin-compatible scoring endpoint. Returns a numerical score (0–10) and a list of specific triggers — phrases like "FREE!!!", excessive capitalization, missing unsubscribe link, image-to-text ratio too high. A score above 3.0 is likely to hit spam folders.

**Tool 3 — check_audience_fatigue:** Queries the campaign history for this specific segment and returns how many campaigns they have received in the last 14 days, the average open rate trend (is it declining?), and whether the current subject line uses the same structural pattern as the last three subject lines sent to this segment. If three consecutive campaigns started with a question ("Did you know...?"), the agent avoids that pattern.

**Tool 4 — predict_ctr_from_history:** A small trained classifier (built from your historical campaign data in Phase 2) that takes a subject line's features — length, has number, has question mark, urgency words present, personalization tokens, day of send — and returns a predicted CTR range based on what similar subject lines achieved in the past.

**Real example:** The Content Generation Agent generates a subject line: "FREE EXCLUSIVE OFFER - Don't Miss Out!!!". It calls `check_spam_score` and gets a score of 7.4 with triggers "excessive capitalization," "FREE in subject," "multiple exclamation marks." It discards this variant. It generates a new one: "3 products your neighbors bought this week." It calls `check_spam_score` — score 0.8, no triggers. It calls `check_audience_fatigue` — this segment has received 2 campaigns this week already, so the agent decides to reduce urgency language. It calls `predict_ctr_from_history` and gets a predicted CTR of 2.8–3.4%, which is above this tenant's historical average of 2.1%. It returns this variant. The entire loop took 4 tool calls and 2 LLM calls, and the output is grounded in real system data rather than GPT's general knowledge about marketing.

---

## Addition 2 — Replace the Linear Graph with a Conditional Graph with Real Cycles

### What This Is

The current LangGraph implementation has edges like A → B → C → D in a straight line. Every campaign execution follows the exact same path regardless of what happens along the way. This is a pipeline. A real agent graph has **conditional edges** — edges whose destination depends on what the agent computed at a node — and **cycles** — edges that point backward to earlier nodes when something fails or needs revision.

### Why This Matters

A straight-line graph cannot represent failure, revision, or iteration. In the real world, a strategy might be generated and then fail the quality gate because the target segment is too small. In the current system this is either ignored or crashes the pipeline. In a conditional graph, failing the quality gate means the graph routes back to the Strategy Agent with the specific failure reason injected into the state, the Strategy Agent generates a revised strategy, and the quality gate re-evaluates. This happens autonomously, without human intervention, until the strategy passes or a maximum retry count is reached.

More importantly, the **human approval loop** currently works as a blocking API call — the system generates content, emails you, and sits there waiting. If the server restarts, the campaign is lost. Real human-in-the-loop in LangGraph uses the `interrupt()` primitive to pause execution, serialize the entire graph state to the database, and resume from that exact checkpoint when the human responds — even if the server has restarted three times in between.

### How the Graph Looks After This Addition

The graph has these nodes: Brief Parser, Segmentation, Strategy, Quality Gate, Content Generation, Human Approval, Execution, Monitoring, Performance Gate, Optimization.

**Brief Parser → Segmentation:** Always. No condition here.

**Segmentation → Strategy:** Always. But the Segmentation node now writes validated, RFM-scored segments into the shared state, not just GPT-generated descriptions.

**Strategy → Quality Gate:** Always. The Quality Gate is a new node that runs deterministic checks — no LLM involved. It checks: are all segments above minimum size, is the proposed send time not within 48 hours of a previous campaign to the same segment, does the budget allocation add up correctly, is there at least one A/B variant proposed. If all checks pass, it routes to Content Generation. If any check fails, it routes back to Strategy with the specific failures listed in the state.

**Strategy (on retry) → Quality Gate:** The Strategy Agent receives the failed checks in its context, adjusts the strategy specifically to address them, and the Quality Gate re-evaluates. Maximum 3 retries before escalating to human.

**Content Generation → Human Approval (interrupt):** The graph pauses here. The state is serialized and saved. A webhook fires to the frontend. The campaign appears in the "Pending Approval" queue in the UI. The human can approve, reject with written feedback, or request specific edits. Each action maps to a different graph edge.

**Human Approval → Execution:** If approved, execution starts.

**Human Approval → Content Generation:** If rejected or edits requested, the rejection reason and specific edit instructions are injected into the state, and Content Generation receives them in its next invocation. The agent reads the feedback and revises accordingly — it does not start from scratch, it refines.

**Execution → Monitoring:** After campaigns are sent, Monitoring starts polling for metrics.

**Monitoring → Performance Gate:** Monitoring checks every 6 hours. The Performance Gate compares open rate, CTR, and unsubscribe rate against this tenant's historical benchmarks. If all metrics are at or above benchmark, it marks the campaign as successful and ends. If any metric is below benchmark by more than 20%, it routes to Optimization.

**Optimization → Content Generation:** The Optimization Agent identifies which variants are underperforming and why, and routes back to Content Generation with specific improvement instructions — not a vague "do better" but "replace the subject line pattern (question + exclamation) with a subject line pattern (number + benefit) based on the performance gap between variants B and C."

**Real example of a full cycle:** A campaign brief is submitted for a winter sale. The Brief Parser extracts the details. Segmentation runs and creates 4 segments. Strategy proposes a plan. Quality Gate runs and finds that Segment 3 is only 90 people — fails the minimum size check. It routes back to Strategy with the message "Segment 3 has 90 members, below the 200 minimum. Merge with nearest segment or remove." Strategy merges Segments 3 and 4 and resubmits. Quality Gate passes all checks. Content Generation creates variants. The graph pauses at Human Approval. The marketing manager opens the UI, reads the subject lines, likes three of them but edits one. She approves. Execution fires the campaign. 12 hours later, Monitoring finds that Variant A's CTR is 0.8% against a 2.1% benchmark. Performance Gate routes to Optimization. Optimization identifies that Variant A used a generic subject line while Variants B and C used personalization tokens, and recommends replacing Variant A with a personalized version. Content Generation regenerates Variant A. The replacement is sent to the underperforming segment. The campaign concludes with a combined CTR of 2.6%.

---

## Addition 3 — Persistent Agent Memory with Two Layers

### What This Is

Agents in the current system have no memory. Every campaign run starts completely fresh — the Content Generation Agent has no idea what subject lines it wrote last week, whether they worked, what the brand guidelines say, or what patterns tend to fail for this particular audience. Adding memory means agents accumulate knowledge over time and their behavior improves with every run.

There are two distinct types of memory with different purposes, different storage mechanisms, and different lifetimes.

### Layer 1 — Run-Level Memory (Short-Term, Within One Campaign)

This is the shared state object that all agents in a single campaign run read and write. Think of it as the campaign's working memory — a structured document that every agent contributes to and reads from as the run progresses.

The state starts with just the campaign brief. After Brief Parser runs, it adds structured extracted fields. After Segmentation runs, it adds the validated segments with their RFM scores. After the Quality Gate runs, it adds a quality check log showing what passed and what failed. After Content Generation runs, it adds the generated variants along with their spam scores and predicted CTRs. After Human Approval, it adds the approval decision and any feedback given. After Execution, it adds the send timestamps and the recipient counts. After each Monitoring poll, it appends the latest metrics.

The critical engineering requirement: this state is **checkpointed to MongoDB after every node completes.** This means if the server crashes at any point in a 3-day campaign lifecycle, the entire run can be resumed from the last checkpoint. An agent re-running after a crash sees the full history of what has already happened — it does not repeat work that was already done.

The state also serves as an **audit log.** Every decision an agent made, every tool it called, every retry it attempted is recorded in the state. This is what you show a sceptical interviewer when they ask "how do you know the agents are working correctly?" — you open the state document and walk through exactly what happened.

### Layer 2 — Cross-Campaign Memory (Long-Term, Persistent Across All Runs)

This is a structured knowledge base backed by pgvector that persists indefinitely. After every campaign completes, the Optimization Agent writes a memory record that captures what was learned.

A memory record contains: the campaign type (product launch, seasonal sale, re-engagement), the audience segment characteristics (RFM tier, age range, purchase category), the subject line patterns that performed above benchmark, the subject line patterns that performed below benchmark, the best performing send time for this audience, the content length that got the highest engagement, and the quantified performance delta between winning and losing variants.

When a new campaign starts and reaches the Content Generation Agent, the agent queries the memory store. It sends the current campaign's brief and audience description as the search query and retrieves the 5 most similar past campaigns by semantic similarity. It then reads through those memories and incorporates the learnings before generating content.

**Real example of memory in action:** In February, a fashion e-commerce brand ran a Valentine's Day campaign to their high-value segment. The Optimization Agent wrote a memory: "Valentine's Day campaign, high-value female segment 25-35, winning subject line pattern: personalized name + gift suggestion, winning send time: Thursday 11am, losing pattern: urgency + discount percentage, CTR lift of winning over losing: 1.8x."

In November, the same brand runs a Diwali campaign to the same segment. Content Generation queries the memory store with "Diwali campaign, high-value female segment 25-35." The Valentine's Day memory comes back as a top result because the audience is identical. The agent reads it and learns: this audience responds to personalized gift suggestions and ignores urgency-based discount framing. It generates subject lines accordingly. Without the memory, it would start from scratch and likely make the same mistakes that failed in February.

The memory grows more valuable with every campaign. After 50 campaigns, the Content Generation Agent has a rich, tenant-specific knowledge base that encodes months of A/B test learnings. This is something a generic GPT-4 call can never replicate — it is institutional knowledge that belongs to the platform.

---

## Addition 4 — Parallel Agent Execution with Fan-Out / Fan-In

### What This Is

Currently, if a campaign targets 4 customer segments, the Content Generation Agent generates content for Segment 1, waits for it to complete, generates content for Segment 2, waits, and so on. This is sequential execution. Adding parallel execution means all 4 segments receive content generation simultaneously, and the graph waits for all 4 to complete before proceeding to the Human Approval node.

This uses LangGraph's `Send` API — a mechanism that dynamically spawns multiple instances of the same node, each with its own state slice, running in parallel. The results are collected at a merge node and combined back into the shared state.

### Why This Matters

There are two reasons this matters — one practical, one architectural.

The practical reason is speed. If each segment's content generation takes 15 seconds (one LLM call for subject lines, one for body, one for spam check, one for CTR prediction), four segments sequentially takes 60 seconds. Four segments in parallel takes 15 seconds plus a small overhead for spawning. For large campaigns with 8 or 10 segments, the difference is minutes.

The architectural reason is more important for your resume. Parallel fan-out / fan-in is a genuinely advanced LangGraph pattern that most developers using LangGraph have never implemented. Most LangGraph tutorials show linear graphs. The `Send` API with dynamic parallelism is an advanced feature documented in LangGraph's internals, not its quickstart. Implementing it correctly demonstrates that you understand the framework at a depth level, not a tutorial level.

### How It Works in Practice

After the Strategy node completes, the graph has a list of validated segments — say, 4 segments. Instead of a single edge from Strategy to Content Generation, the graph has a **fan-out node** that inspects the segments list and dynamically creates one Content Generation task per segment. Each task carries the full shared state plus the specific segment it is responsible for.

The 4 Content Generation tasks run concurrently. Each one runs its own tool loop — querying brand guidelines, checking spam scores, predicting CTR, checking audience fatigue — independently. Each one produces its own set of variants with its own spam scores and performance predictions.

When all 4 complete, a **merge node** collects the results, combines the variants into a single content package organized by segment, and routes to the Human Approval node. The human sees all 4 segments' content in one review interface, not sequentially.

**Real example:** A campaign targets four segments: Champions (top 20% by RFM), Loyal Customers, At-Risk Customers, and New Customers. Each segment needs different messaging — Champions get early access and exclusivity messaging, Loyal Customers get loyalty rewards messaging, At-Risk Customers get win-back offers, New Customers get onboarding and discovery messaging. These four content generation tasks have zero dependency on each other. Running them in parallel is not just an optimization — it is architecturally correct, because they are genuinely independent tasks. The fan-out / fan-in pattern makes this independence explicit in the graph topology.

---

## Addition 5 — A Real Optimization Agent with Statistical Grounding

### What This Is

The Optimization Agent in the current system receives performance metrics and calls GPT with a prompt like "here are the open rates for each variant, suggest improvements." GPT produces generic marketing advice based on its training data. This advice may or may not be relevant to this specific audience, this specific product, or this specific brand.

The real Optimization Agent uses the LLM only as the last step — for synthesis and text generation. Every analytical step before the LLM call is done in code, using real statistics, real comparisons against real historical data. The LLM receives a brief, evidence-backed problem statement and generates targeted solutions, not general advice.

### The Tools the Optimization Agent Uses

**Tool 1 — run_statistical_significance_test:** Takes two variants' performance numbers — open rates with sample sizes — and runs a chi-square test. Returns whether the difference between the variants is statistically significant (p-value below 0.05) or whether it could be random noise. This is critical because most A/B test "winners" in small campaigns are actually just noise. The agent will not flag a variant as underperforming unless the difference is statistically significant. Without this tool, the agent might replace a "losing" variant that actually performed fine and was just unlucky in the random assignment.

**Tool 2 — compute_feature_delta:** Takes the two best-performing and two worst-performing variants and extracts their structural features — subject line length, presence of personalization token, number of words in the CTA, use of urgency language, use of numbers, email body length, image-to-text ratio. Returns a feature comparison table showing which features correlate with better performance in this specific campaign run. This is not GPT's general marketing advice — it is data from this specific campaign, for this specific audience.

**Tool 3 — retrieve_similar_campaign_learnings:** Queries the long-term memory store for past campaigns with similar parameters — same audience segment type, similar product category, similar campaign objective. Returns the performance patterns that have been stable across multiple past runs. If 5 past campaigns to similar audiences all show that subject lines with the recipient's first name outperform those without by an average 1.4x, that pattern is strong evidence and should inform the optimization.

**Tool 4 — compute_audience_fatigue_score:** Checks how many campaigns this segment has received in the last 30 days and whether the CTR trend across those campaigns is declining. A declining trend despite changing content suggests the audience is fatigued — the correct optimization in that case is to reduce campaign frequency and extend the re-engagement interval, not to rewrite the content.

### How the Agent Uses These Tools Together

The agent first calls the statistical significance test to determine which underperformances are real and which are noise. It only proceeds to optimize variants whose underperformance is statistically confirmed. It then calls the feature delta tool to understand structurally what is different between the winning and losing variants. It then calls the memory store to see if this pattern (say, urgency language underperforming for this audience type) has appeared in past campaigns. If it has appeared in 4 of 5 similar past campaigns, the agent has strong evidence for its recommendation.

Only at this point does it call the LLM. The prompt it sends is not "here are metrics, suggest improvements." It is: "Variant A's open rate is 1.2% vs Variant B's 3.1% — this difference is statistically significant at p=0.001. Feature analysis shows Variant A uses urgency framing ('Last chance, offer expires tonight') while Variant B uses curiosity framing ('3 items that sold out last season just came back'). Historical memory shows urgency framing has underperformed curiosity framing for this High-Value Female segment in 4 of 5 past campaigns. Generate 3 replacement variants for Variant A that use curiosity or personalization framing, each with a subject line under 55 characters."

The LLM now has a specific, evidence-backed brief. The output is targeted and grounded, not generic.

**Real example:** A re-engagement campaign has 4 variants. After 24 hours, the chi-square test confirms Variants C and D are performing significantly below Variants A and B. Feature delta shows C and D both use a discount percentage in the subject line ("Get 30% off today") while A and B use product recommendations ("Items waiting in your cart"). Memory retrieval shows this audience segment responded poorly to discount-first messaging in 3 previous campaigns but responded 2.1x better to product-specific messaging. The agent sends a targeted prompt to the LLM and receives 3 replacement variants using product recommendation framing. Variants C and D are replaced in the live campaign.

---

## Addition 6 — Observability Layer with LangSmith Tracing

### What This Is

Observability means you can look inside a running or completed agent system and understand exactly what happened, step by step — which nodes ran, in what order, what each agent received as input, what tools it called, what the tool returned, what the LLM received, what the LLM returned, how long each step took, and how many tokens it consumed.

Without observability, your agentic system is a black box. Something goes wrong — a campaign generates bad content, an agent loops unexpectedly, the system takes 3 minutes for a task that should take 20 seconds — and you have no way to debug it except adding print statements and re-running.

LangSmith is Anthropic's LangChain's tracing platform. Every LangGraph run automatically emits a structured trace — a hierarchical view of every node invocation, every LLM call within that node, every tool call within that LLM call, with latencies and token counts at each level. This is added to the system as a one-line configuration change, but the value it delivers is enormous.

### What the Observability Layer Captures

**Execution traces:** For every campaign run, a complete tree showing the sequence of nodes, conditional routing decisions, retries, and parallel executions. You can see that for Campaign #47, the graph went through the Quality Gate 3 times (meaning Strategy had to revise twice), that Content Generation ran in parallel for 4 segments (taking 18 seconds instead of the sequential 64 seconds), and that the Human Approval node was pending for 14 hours before the marketing manager responded.

**Agent decision logs:** For every LLM call, the exact prompt that was sent and the exact response that was received, timestamped. This is how you detect prompt injection (a user's campaign brief containing instructions that hijack the agent's behavior), hallucinations (the agent claiming historical performance data that does not exist in the memory store), and reasoning errors (the agent misinterpreting a tool output).

**Tool call logs:** For every tool call, the input parameters and the returned output. This lets you verify that the Segmentation Agent's clustering tool was called with the correct feature matrix, that the spam checker returned a score of 1.2 (not 7.4 as it would for a different input), and that the memory retrieval query returned relevant records (not empty results due to a misconfigured embedding).

**Cost tracking:** Every LLM call is tagged with the node, agent, campaign ID, and tenant ID. This means you can answer: how much did Campaign #47 cost in total LLM tokens? Which agent is the most expensive? Is the Optimization Agent making redundant LLM calls that could be eliminated? For a multi-tenant platform, this becomes: which tenant's campaigns cost the most and are those costs covered by their subscription tier?

**Latency analysis:** Which node is the bottleneck? If the average campaign takes 3 minutes, the trace shows that 2.1 minutes are spent in Content Generation (the parallel execution should address this), 40 seconds in Segmentation, and 20 seconds in Strategy. Knowing this prioritizes where optimization effort should go.

### Why This Is Important for Your Resume

Most agentic AI projects have no way to answer the question "how do you know it's working?" You can show a demo where it works once, but an interviewer at a serious AI company will ask about failures, edge cases, and debugging. Having a complete observability layer with traces, cost data, and latency breakdowns is the answer to that question. It shows you think about the system as a production artifact, not just a demo.

---

---

# PHASE 2 — Expanding the Problem Statement

## The Transition from Tool to Platform

Phase 1 turns CampaignX into a genuinely agentic system. Phase 2 turns it from a single-business tool into a **platform** — a system that manages multiple businesses, learns across all of them, operates autonomously, and improves continuously. The problem statement expands from "automate marketing campaigns for one business" to "build an AI-native marketing intelligence platform that gets measurably smarter with every campaign it runs, across every business it serves."

This is a problem statement that justifies genuine complexity. It introduces challenges that only exist at scale — data isolation, cross-tenant learning, model specialization, real-time event processing, adversarial robustness — that a single-business tool never encounters.

---

## Addition 7 — Multi-Tenancy with Federated Agent Memory

### What This Is

Multi-tenancy means the platform serves multiple businesses simultaneously, with each business's data, agents, and memory completely isolated from others. A fashion brand's customer segments, campaign history, and brand guidelines are never accessible to a food delivery startup using the same platform.

Federated memory is the layer on top of isolation that enables **learning without data sharing.** The core insight is that some patterns are universal ("subject lines with the recipient's first name outperform generic ones") while others are company-specific ("our customers respond to festival-themed promotions in October"). The federated memory architecture separates these two categories: universal patterns go into a shared knowledge base, company-specific data stays isolated.

### Why This Is Hard

The naive implementation of multi-tenancy is simple — add a `tenant_id` field to every database record and filter by it everywhere. That solves isolation. The hard part is federated learning.

Consider this scenario: Tenant A (a fitness brand) runs 50 campaigns and discovers that their audience responds 2x better to transformation story subject lines than to discount-first subject lines. Tenant B (a different fitness brand, no relationship to Tenant A) starts their first campaign. Without federated learning, Tenant B starts from zero — no historical data, no learned patterns. With federated learning, Tenant B's Content Generation Agent can benefit from the pattern learned across 50 campaigns without ever seeing Tenant A's customer data, campaign content, or performance numbers.

The mechanism is **abstraction.** When Tenant A's Optimization Agent writes a memory record, it writes two versions: a tenant-specific record (with actual CTR numbers, actual segment demographics, actual subject line text) stored in Tenant A's isolated namespace, and an abstracted record (with normalized performance ratios, anonymized audience tier labels, structural subject line patterns without actual words) stored in the shared knowledge base.

Tenant B's agents can query the shared knowledge base and learn that "transformation story framing outperforms discount framing by 2x for mid-value fitness audiences" — without learning anything about Tenant A's actual customers, subject line copy, or business metrics.

### How the Architecture Works

Each tenant gets a dedicated namespace in the pgvector store. All tenant-specific memories — actual campaign content, actual performance numbers, actual customer segment descriptions — live in this namespace. Queries from Tenant B cannot access Tenant A's namespace.

The shared knowledge base is a separate collection where only abstracted, anonymized patterns are written. The abstraction layer is a transformation function that runs before every memory write — it strips identifying information, normalizes metrics to relative scales (percentile ranks, not absolute numbers), and converts specific content to structural patterns.

A background process called the Pattern Aggregator runs nightly across all tenant memories. It looks for patterns that appear consistently across 5 or more tenants — these are likely universal truths about email marketing, not tenant-specific quirks. When it finds such a pattern, it elevates it into a "high-confidence universal insight" that all tenants' agents can use with higher weight.

**Real example:** Ten different tenants all run re-engagement campaigns to dormant customers. Nine of the ten find that subject lines offering a specific product recommendation outperform subject lines offering a generic discount. The Pattern Aggregator detects this as a strong universal pattern and elevates it. Tenant 11, a brand new customer on the platform running their first re-engagement campaign, immediately benefits from this insight — their Content Generation Agent recommends product-specific subject lines over discount subject lines because of the universal pattern, without having run a single campaign themselves.

This is a genuinely novel architectural contribution. It solves a real problem that every SaaS platform faces: how do you give new customers the benefit of accumulated platform intelligence without violating the privacy of existing customers?

---

## Addition 8 — Event-Driven Autonomous Monitoring Agent

### What This Is

The current Monitoring Agent runs on a schedule — every 6 hours, poll the metrics API, check if performance is above or below benchmark, report. This is polling-based monitoring. It is passive, delayed, and cannot respond to events that happen between polling intervals.

Event-driven monitoring means the Monitoring Agent is continuously subscribed to a stream of real-world signals. When a signal arrives that requires action, the agent wakes up, reasons about the signal, and acts — without any human initiating the process. The agent is always on, not periodically on.

### The Signal Stream

The platform subscribes to multiple signal sources through a Redis Streams (or Kafka) event bus. Signals arrive as structured events and are routed to the Monitoring Agent.

**Internal signals** are generated by the platform itself: a campaign's open rate drops more than 30% in a 2-hour window (abnormal decline, possibly a deliverability issue), an unsubscribe rate spikes above 2% in an hour (content may be irrelevant or offensive), a click rate on a specific variant suddenly exceeds expectations by 3x (a viral moment that should be amplified), a scheduled campaign is about to send to a segment that received a different campaign 18 hours ago (audience fatigue risk).

**External signals** are sourced from outside the platform: a competitor sends an email campaign (detected by the competitor monitoring tool), a major news event occurs that makes the scheduled campaign tone-deaf (a planned "flash sale" campaign scheduled during a national tragedy), a product featured in an upcoming campaign goes out of stock (real-time inventory integration), a social media post about the brand goes viral and generates 10x normal traffic (opportunity to amplify with a timely campaign).

### How the Agent Responds

For each signal type, the agent has a **response playbook** — a set of possible actions ordered by urgency and reversibility. The agent reasons about the signal, consults the playbook, and chooses an action.

For an unsubscribe spike, the playbook is: first, pause the campaign immediately (reversible, low risk), then analyze which variant is driving the unsubscribes (was it a specific segment? a specific subject line?), then notify the human via the dashboard with a specific question ("Variant C has a 4.1% unsubscribe rate, 3x normal. Recommend removing Variant C and replacing with a revision. Approve?"), then wait for approval before resuming.

For a competitor campaign detection, the playbook is: extract the competitor's subject line and offer structure from the email, query the memory store for how this brand has historically responded to competitive pressure, generate a counter-campaign brief (a rapid-response campaign highlighting a differentiating feature), and present it to the marketing manager as an optional action — not auto-execute, because competitive response is a strategic decision that should involve humans.

For a product going out of stock, the playbook is: immediately pause all campaigns that feature the out-of-stock product, update the product recommendation tool to exclude that product, and if there are already-sent campaigns directing customers to a landing page featuring that product, trigger an automated email to those customers redirecting them to an alternative product. This entire sequence executes autonomously without human intervention — it is routine and time-critical.

**Real example of event-driven autonomous action:** It is 11pm on a Tuesday. A fashion brand's campaign is scheduled to send at 8am Wednesday to 12,000 customers featuring a specific handbag. At 11:43pm, the inventory system publishes an event: "Product SKU-7821 (handbag) stock: 0." The Monitoring Agent receives this event within 30 seconds. It pauses the Wednesday campaign, queries the product catalog for the top 3 alternatives with similar price point and style, regenerates the campaign content featuring those alternatives, runs spam check and CTR prediction on the new content, and sends a dashboard notification to the marketing manager: "Wednesday campaign updated — original product out of stock, replaced with 3 alternatives. Campaign ready to send at 8am as scheduled. Review changes here." The marketing manager wakes up to a notification, reviews the changes in 2 minutes, approves, and the campaign sends on time. Without the event-driven agent, they would have sent 12,000 emails advertising a product customers could not buy.

### The Competitor Intelligence Tool

This tool deserves its own explanation because it is architecturally interesting. The system subscribes to competitors' email lists under a monitoring inbox. When a competitor email arrives, the tool extracts the subject line, the offer type (discount, free shipping, exclusive access, urgency), the product categories featured, and the estimated send time. This data is stored in a competitor intelligence database indexed by competitor, date, and campaign type.

The Monitoring Agent queries this database when generating competitor response recommendations. Over time, patterns emerge — a specific competitor always does a major promotion in the first week of every month, another competitor has started sending more frequently (possible indication of a customer acquisition push). These patterns inform the brand's own timing and positioning strategy.

This is not a new idea in marketing — competitor monitoring is standard practice. What is new is that the analysis and response recommendation is autonomous and real-time, not a manual weekly review process.

---

## Addition 9 — Agent Specialization via Fine-Tuning on Campaign Outcomes

### What This Is

After the platform has run 50 or more campaigns, it has generated a gold dataset that no other system has: pairs of (campaign brief + audience description + content variant) mapped to (actual open rate, actual CTR, actual conversion rate). This is outcome-labeled training data for marketing copy generation.

Agent specialization means using this data to fine-tune a small open-source language model — specifically Llama 3.1 8B using LoRA adapters — to become a specialized marketing copy generation model that has internalized what actually works for the platform's specific audience base, product categories, and brand voices.

This model is called the **CampaignX Content Intelligence Model (CCIM)** and it replaces GPT-4 as the primary model for the Content Generation Agent after sufficient training data has accumulated.

### Why This Is a Research-Grade Contribution

Fine-tuning is a well-understood technique. What makes this contribution novel is the **nature of the labels.**

Most fine-tuning for text generation uses human preference labels — human raters read two outputs and choose which one they prefer. This is called RLHF (Reinforcement Learning from Human Feedback) and it is how GPT-4 and Claude are aligned. Human preference labels have a well-known problem: human raters often prefer text that sounds confident and well-written, not text that actually achieves the desired outcome.

The CCIM uses **outcome-based labels** — actual open rates and CTRs from real email campaigns sent to real people. A subject line that sounds boring to a human rater but has a 4.2% open rate against a 2.1% benchmark is labeled as a positive example. A subject line that sounds dynamic and engaging but has a 0.8% open rate is labeled as a negative example. The labels come from reality, not human opinion.

This distinction is publishable. The paper argues: "outcome-based fine-tuning for marketing copy generation produces more effective content than human preference fine-tuning because it optimizes for real behavioral outcomes rather than surface-level text quality judgments."

### The Training Pipeline

After 50 campaigns have completed with full metrics, the training data construction process begins. Each completed campaign contributes multiple training examples — one per variant per segment. A variant sent to Segment A is a different data point than the same variant sent to Segment B, because the audience is different.

Each training example contains: the campaign brief (product description, campaign objective, audience tier), the audience segment's RFM profile and historical engagement patterns, the generated variant (subject line + email body), and the outcome labels (open rate normalized as a percentile rank among all campaigns to that segment type, CTR similarly normalized).

The training objective is: given a brief and audience description, generate content that would achieve a high percentile rank on open rate and CTR. The normalization to percentile ranks is important — it makes the labels comparable across different tenants who have different absolute CTR baselines (B2B campaigns typically have lower CTRs than e-commerce campaigns, so 1.5% might be excellent for one tenant and poor for another).

Fine-tuning runs on a weekly batch schedule using accumulated new campaign data. The model is evaluated on a held-out test set before each deployment — if the new model does not outperform the previous version on the held-out set, it is not deployed. Model versioning is tracked in MLflow.

### The Content Generation Agent's Dual-Mode Operation

The Content Generation Agent operates in two modes based on available training data.

In cold-start mode (fewer than 20 completed campaigns for this tenant), it uses GPT-4 with RAG over the shared knowledge base. It has no tenant-specific fine-tuned model and no tenant-specific memory to draw from.

In warm mode (20 or more completed campaigns), it switches to the CCIM for initial draft generation. The CCIM is a smaller model (8B parameters vs GPT-4's estimated 1T+ parameters) and runs faster and cheaper. Its output is then passed through the spam checker and CTR predictor tools. If any tool flags a problem, the agent uses GPT-4 for a targeted revision of the flagged section — not a full regeneration, just a targeted fix.

This hybrid approach is architecturally interesting: the specialized small model does the bulk generation cheaply and quickly, and the large general model serves as a quality-checking editor. The total cost per campaign decreases significantly compared to using GPT-4 for all generation.

---

## Addition 10 — Multi-Agent Debate for High-Stakes Decisions

### What This Is

For campaign runs above a certain risk threshold — defined as budget above a configurable limit, audience above a configurable size, or first-ever campaign in a new product category — the system activates a **deliberation protocol** involving multiple agents with different roles and incentives.

Instead of the Strategy Agent proposing a plan and it proceeding to Content Generation, the plan goes through a structured debate process: a proposal phase, a critique phase, a revision phase, and a risk scoring phase. Only after passing all four phases does the plan proceed.

### Why Single-Agent Decisions Fail at High Stakes

A single agent — even a well-equipped one with tools and memory — has a systematic bias: it is rewarded for producing confident, complete-sounding outputs. It rarely says "I am not sure" or "this plan has a serious risk that I cannot resolve." This is a fundamental property of autoregressive language models, not a bug in a specific prompt.

For a low-budget test campaign to 500 people, this bias does not matter much. A suboptimal strategy costs little. For a campaign to 500,000 customers announcing a major price change, a confident but wrong strategy from a single agent can cause significant brand damage. The multi-agent debate introduces structural adversarialism — an agent whose job is to find weaknesses, not propose solutions.

### The Four Agents in the Debate

**The Strategist Agent:** Proposes the campaign plan in detail — target segments, content strategy, timing, A/B test design, budget allocation. This is the current Strategy Agent, unchanged. Its output is the initial proposal.

**The Devil's Advocate Agent:** Receives the Strategist's proposal and its only job is to find problems. It uses specific tools to ground its criticism: `check_past_failed_campaigns` (queries the memory store for campaigns with similar parameters that failed and extracts why they failed), `compute_audience_fatigue_score` (checks if the proposed segments have been over-contacted recently), `verify_regulatory_compliance` (checks the proposed content against a database of advertising regulatory guidelines — ASCI guidelines in India, CAN-SPAM compliance, GDPR compliance for European audiences if relevant). The Devil's Advocate returns a structured critique — not vague concerns, but specific issues with evidence. "Segment B received 3 campaigns in the last 10 days. Unsubscribe rate has been trending up 15% per campaign. Proposing to send to them again this week has a 72% probability of accelerating churn based on historical patterns."

**The Strategist Agent (revision):** Receives the structured critique and revises the proposal to address the specific issues. This is not a new agent — it is the same Strategist Agent running again with the critique injected into its context. For each criticism, it either resolves it (changes the strategy to avoid the problem) or explicitly argues why the criticism does not apply in this case (provides counter-evidence from the memory store).

**The Risk Assessment Agent:** Receives the revised proposal and produces a final risk score across four dimensions: brand safety (does the content risk reputational damage?), audience risk (is there a meaningful churn probability?), financial risk (is the budget allocation proportional to the expected return based on historical data?), and compliance risk (are there any regulatory issues?). Each dimension is scored 0–10 and the scores are computed using tools and memory data, not LLM intuition. The aggregate score determines whether the campaign auto-proceeds or gets escalated to a human for final approval.

**Real example:** A consumer electronics brand plans a campaign to their entire customer base (220,000 people) announcing a discontinuation of a popular product line. The Strategist proposes the campaign. The Devil's Advocate checks past campaigns and finds three examples where similar "product discontinuation" announcements caused 4–8% unsubscribe spikes and generated significant negative sentiment in customer replies. It also flags that the proposed send time (Friday afternoon) historically has the lowest engagement rates for this brand's audience. The Strategist revises: it changes the framing from "discontinuation" to "product evolution with upgrade path," changes the send time to Tuesday morning, and adds a personalized upgrade recommendation based on each customer's purchase history. The Risk Assessment Agent scores the revised plan: brand safety 8/10, audience risk 7/10 (still high but improved), financial risk 9/10, compliance risk 10/10. Average 8.5/10, above the auto-approval threshold of 7.5. The campaign proceeds. The unsubscribe rate on the actual send is 0.3% — within normal range.

---

## Addition 11 — Natural Language Campaign Control via Supervisor Agent

### What This Is

Currently, managing campaigns requires navigating a UI — clicking through forms to create a campaign, clicking buttons to approve content, navigating to a metrics page to check performance. This is fine for routine operations but becomes cumbersome for complex multi-campaign management: "pause all campaigns to dormant customers and resume them with last month's best-performing variants once they have been dormant for 30 days."

The Supervisor Agent is a new top-level agent that accepts natural language instructions and translates them into concrete actions across the entire platform. It has access to every other agent and every platform capability as tools. The user types instructions in plain language and the Supervisor Agent orchestrates whatever combination of agents, database operations, and scheduled tasks is required.

### How the Supervisor Agent Differs from a Chatbot

This distinction is important and will come up in interviews. A chatbot answers questions. The Supervisor Agent executes actions on live systems.

When a user asks a chatbot "which campaigns are underperforming?", the chatbot queries the database and reports the answer. When the same user tells the Supervisor Agent "pause all underperforming campaigns and schedule an optimization run for each one in 4 hours," the agent pauses live campaigns (modifying their status in the database and halting any scheduled sends), creates scheduled jobs for the Optimization Agent to run at the specified times, and confirms the actions taken with a summary the user can verify.

The user is not configuring a workflow through a UI. They are issuing instructions in natural language and the agent is deciding what actions to take, in what order, with what parameters. This requires the agent to handle ambiguity (what does "underperforming" mean for this tenant's historical benchmarks?), ask clarifying questions when the instruction is genuinely ambiguous (does "last month's best-performing variants" mean highest open rate or highest CTR?), and confirm before taking irreversible actions (pausing a live campaign that has already been sent to 50% of its audience cannot be fully undone).

### Ambiguity Resolution

This is the hardest engineering problem in the Supervisor Agent and also the most important one to get right. Most natural language interfaces either ignore ambiguity (just guess and hope) or ask too many clarifying questions (annoying and unusable).

The Supervisor Agent uses a **confidence threshold** approach. When parsing an instruction, it assigns a confidence score to each interpretation. If the confidence for the top interpretation is above 0.85 (the intent is clear), it proceeds. If it is between 0.60 and 0.85 (the intent is probable but could be misread), it proceeds but summarizes its interpretation before executing and asks for confirmation. If it is below 0.60 (genuinely ambiguous), it asks exactly one clarifying question — the most important ambiguity to resolve — before proceeding.

**Real example of the agent handling a complex instruction:** The marketing manager sends: "Run a win-back sequence for everyone who hasn't purchased in 90 days — first email is soft re-engagement, second email 3 days later is a product recommendation, third email 5 days after that is a time-limited offer. Use our Q3 top performers as the template."

The Supervisor Agent parses this and identifies: a three-email drip sequence, specific timing intervals, a specific audience definition (no purchase in 90 days), and a reference to "Q3 top performers" that needs to be resolved. It queries the memory store for Q3's top-performing campaigns by open rate and CTR, retrieves the subject line patterns and content structures from those campaigns, and identifies that "Q3 top performers" maps to 3 specific campaigns. It then creates a campaign sequence in the database with three scheduled sends, configures the audience filter, populates the content templates with Q3 patterns as the starting point for the Content Generation Agent, and runs the segmentation and content generation pipeline for all three emails in parallel.

It then reports: "I have created a 3-email win-back sequence for 4,218 customers with no purchase in 90 days. Email 1 uses the re-engagement tone from Campaign 34 (your Q3 top performer by open rate — 4.1%). Email 2 will trigger 3 days after Email 1 is opened. Email 3 triggers 5 days after Email 2. Emails 2 and 3 are pending content generation. First draft will be ready for review in approximately 8 minutes. Confirm sequence setup?"

This single natural language instruction replaced approximately 25 minutes of UI navigation across the campaign creation, audience management, and scheduling interfaces.

---

## Addition 12 — AgentEval: Evaluation Framework for Agent Quality

### What This Is

AgentEval is an internal framework that continuously measures whether the agents are actually working — not whether the system runs without errors, but whether the agents' decisions are sound, their outputs are grounded, their predictions are accurate, and their costs are justified.

Most agentic AI projects have no answer to the question "how do you know the agents are making good decisions?" They point at demo outputs and hope for the best. AgentEval makes this question answerable with data.

### The Four Evaluation Dimensions

**Dimension 1 — Task Completion Rate:** What percentage of campaign runs complete from brief submission to execution without requiring human intervention beyond the intentional Human Approval checkpoint? A healthy system should complete above 80% of campaigns autonomously. If the rate is 45%, it means the Quality Gate is rejecting strategies too aggressively, or the Content Generation Agent is consistently failing spam checks, or the graph is getting stuck in retry loops. The task completion rate surfaces these problems in aggregate, prompting investigation.

**Dimension 2 — Decision Accuracy:** For campaigns where the Optimization Agent predicted that Variant X would outperform Variant Y, was that prediction correct after the campaign completed? This creates a prediction log: every time the system makes a performance prediction (through the CTR predictor tool or the Optimization Agent's recommendations), the prediction is recorded. After the campaign completes, the actual outcome is compared to the prediction. The accuracy of these predictions is tracked over time — it should improve as the memory store grows and the CCIM is fine-tuned on more data. If prediction accuracy is declining, it suggests model drift or a change in audience behavior that the system has not adapted to.

**Dimension 3 — Hallucination Rate:** This is the most technically interesting evaluation dimension. When an agent makes a factual claim — "urgency framing has historically outperformed curiosity framing for this segment by 1.8x" — that claim should be verifiable against the memory store. The hallucination detector is a background process that intercepts agent outputs, extracts factual claims, queries the memory store to verify each claim, and flags claims that have no supporting evidence.

A hallucination in the context of a marketing agent is not a factual error about the world — it is an unsupported assertion about performance patterns that the agent states with confidence but that does not exist in the historical data. These hallucinations are dangerous because they can lead the agent to make confident recommendations based on invented patterns. Tracking the hallucination rate and alerting when it rises above a threshold is a concrete safety measure for production agentic systems.

**Dimension 4 — Cost Efficiency:** Every LLM call is logged with its token count, the model used, and the node that generated it. The Cost Efficiency metric tracks: total cost per campaign (should decrease over time as the CCIM takes over more generation from GPT-4), cost per agent node (are some agents making redundant LLM calls that could be eliminated or cached?), and cost anomalies (a campaign that costs 10x the average is a signal that the graph looped excessively or a prompt caused the LLM to generate unusually long outputs).

### The AgentEval Dashboard

All four dimensions are surfaced in a live dashboard visible to the system operator. The dashboard shows:

A time-series chart of task completion rate over the last 30 days — ideally trending upward as the system matures. A scatter plot of predicted CTR vs actual CTR for all campaigns in the last 90 days — the tighter the cluster around the diagonal, the better the system's predictions. A hallucination rate gauge showing the percentage of agent claims that were unverifiable against the memory store in the last 7 days. A cost breakdown by tenant, agent, and campaign type showing where LLM spending is concentrated and whether it is proportional to business value delivered.

Beyond the dashboard, AgentEval generates a weekly report that is automatically delivered to the platform operator. The report includes: which campaigns had the highest and lowest task completion rates and why, which agents had the highest hallucination rates and what the specific unverifiable claims were, whether the CCIM's prediction accuracy has improved or degraded since the last model update, and a cost efficiency analysis with specific recommendations for reducing LLM spend without reducing output quality.

**Real example of AgentEval catching a real problem:** The hallucination detector flags that in 7 of the last 15 campaigns, the Content Generation Agent claimed "personalization tokens increase open rate by 25% for High-Value segments" without this pattern existing in the memory store (because High-Value segment personalization data was only collected starting 3 campaigns ago — insufficient for a 25% claim). The agent was hallucinating a specific statistic. The AgentEval report surfaces this, the operator updates the agent's prompt to require statistical claims be referenced to specific memory records, and the hallucination rate for that agent drops to zero in subsequent runs.

---

# Summary — All 12 Additions at a Glance

## Phase 1 — Corrections

| Addition | Core Change | What It Fixes |
|---|---|---|
| 1 — Real Tool Use | Every agent gets code-based tools for database queries, statistical computation, API calls | Agents are no longer asking GPT to guess at things that should be computed |
| 2 — Conditional Graph with Cycles | Replace linear A→B→C with conditional routing and backward edges | System can retry, self-correct, and implement genuine human-in-the-loop |
| 3 — Two-Layer Memory | Run-level state checkpointing + cross-campaign pgvector memory store | Agents accumulate knowledge over time; runs survive server restarts |
| 4 — Parallel Execution | Fan-out / fan-in for segment-level content generation | Eliminates sequential bottleneck; demonstrates advanced LangGraph usage |
| 5 — Statistical Optimization | Optimization Agent uses chi-square tests, feature deltas, and memory retrieval before calling LLM | Recommendations are evidence-based, not generic GPT marketing advice |
| 6 — Observability | LangSmith tracing of all nodes, tools, LLM calls, costs, latencies | System is debuggable and auditable; answers "is it working?" with data |

## Phase 2 — Expansions

| Addition | Core Change | What It Adds |
|---|---|---|
| 7 — Multi-Tenancy + Federated Memory | Isolated tenant namespaces with anonymous cross-tenant pattern sharing | Platform serves N businesses and gets smarter from all of them without data leakage |
| 8 — Event-Driven Monitoring | Continuous signal subscription with autonomous response playbooks | System acts on real-world events without human initiation |
| 9 — Fine-Tuning on Outcomes | Llama 3.1 8B CCIM fine-tuned on actual campaign CTR/open rate data | Specialized model that improves with platform usage; novel research contribution |
| 10 — Multi-Agent Debate | Strategist / Devil's Advocate / Risk Assessment deliberation protocol | High-stakes campaigns get adversarial review before execution |
| 11 — Supervisor Agent | Natural language interface that orchestrates all platform capabilities | Complex multi-campaign management via plain English instructions |
| 12 — AgentEval | Continuous measurement of task completion, prediction accuracy, hallucination rate, costs | Concrete answer to "how do you know the agents are working?" |

---

> **Final note on sequencing:** Implement Phase 1 completely before starting Phase 2. A Phase 2 built on a Phase 1 that was done superficially will have compounding architectural debt that makes every subsequent addition harder. The multi-tenancy in Addition 7, for example, depends on the memory architecture from Addition 3 being implemented correctly. The fine-tuning in Addition 9 depends on the observability from Addition 6 to have reliable training labels. Phase 1 is the foundation — build it properly.
