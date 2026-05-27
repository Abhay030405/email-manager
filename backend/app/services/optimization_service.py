"""Optimization service — orchestrates the full optimization feedback loop."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.db.repositories.optimization_repo import OptimizationRepository
from app.models.optimization import OptimizationResult
from app.services.ab_testing_service import ABTestingService
from app.services.performance_scoring_service import PerformanceScoringService
from app.services.variant_regeneration_service import VariantRegenerationService

logger = logging.getLogger(__name__)


class OptimizationService:
    """Orchestrates the full optimization workflow:
    analyse → insights → regenerate → A/B test → converge.
    """

    def __init__(
        self,
        optimization_agent: Any,
        variant_regeneration_service: VariantRegenerationService,
        ab_testing_service: ABTestingService,
        performance_scoring_service: PerformanceScoringService,
        optimization_repo: OptimizationRepository,
        metrics_repo: Any,
    ) -> None:
        self.optimization_agent = optimization_agent
        self.regeneration_svc = variant_regeneration_service
        self.ab_testing_svc = ab_testing_service
        self.scoring_svc = performance_scoring_service
        self.optimization_repo = optimization_repo
        self.metrics_repo = metrics_repo

    # ── Full workflow ─────────────────────────────────────────────────────────

    async def execute_full_optimization_workflow(
        self,
        campaign_id: str,
        max_iterations: int = 3,
        convergence_threshold: float = 0.05,
        enable_ab_testing: bool = True,
    ) -> dict[str, Any]:
        """Run the iterative optimization loop until convergence or max_iterations."""
        iteration_count = 0
        converged = False
        iteration_results: list[OptimizationResult] = []
        initial_score: Optional[float] = None

        logger.info(
            "Starting optimization for campaign %s (max_iter=%d threshold=%.2f)",
            campaign_id, max_iterations, convergence_threshold,
        )

        while not converged and iteration_count < max_iterations:
            iteration_count += 1
            logger.info("Optimization iteration %d/%d for %s", iteration_count, max_iterations, campaign_id)

            # 1. Collect current metrics
            metrics_list = await self.metrics_repo.find_by_campaign(campaign_id)
            metrics_dicts = [m.model_dump() for m in metrics_list]

            if not metrics_dicts:
                logger.info("No metrics for campaign %s — stopping optimization", campaign_id)
                break

            # 2. Analyse opportunity
            opportunity = await self.optimization_agent.analyze_optimization_opportunity(
                campaign_id, metrics_dicts
            )

            prev_score = opportunity["overall_performance"]
            if initial_score is None:
                initial_score = prev_score

            # 3. Check if improvement potential justifies another iteration
            if opportunity["improvement_potential"] < 0.1:
                logger.info("Improvement potential too low (%.2f) — stopping", opportunity["improvement_potential"])
                converged = True
                break

            poor_performers = opportunity["poor_performers"]
            if not poor_performers:
                logger.info("No poor performers identified — stopping")
                break

            # 4. Generate insights
            insights = await self.optimization_agent.generate_optimization_insights(
                campaign_id,
                poor_performers,
                opportunity["segment_analysis"],
                [],
            )

            # 5. Regenerate variants
            new_variants = await self.regeneration_svc.regenerate_variants(
                campaign_id=campaign_id,
                poor_performers=poor_performers,
                insights=insights,
                iteration_number=iteration_count,
            )

            # 6. Optional A/B testing on newly regenerated variants
            ab_test_results: list[dict[str, Any]] = []
            if enable_ab_testing and len(new_variants) >= 2:
                try:
                    ab_result = await self._run_ab_test(
                        campaign_id, poor_performers[0]["variant_id"], new_variants[0]["variant_id"]
                    )
                    ab_test_results.append(ab_result)
                except Exception as exc:
                    logger.warning("A/B test failed: %s", exc)

            # 7. Store iteration result
            opt_result = OptimizationResult(
                campaign_id=campaign_id,
                iteration_number=iteration_count,
                analyzed_metrics={"variant_count": len(metrics_dicts), "avg_score": prev_score},
                poor_performer_variants=[p["variant_id"] for p in poor_performers],
                optimization_insights=insights,
                recommendations=[i.get("recommendation", "") for i in insights],
                regenerated_variants=new_variants,
                previous_performance_score=prev_score,
                new_performance_score=prev_score,
                improvement_percentage=0.0,
                status="completed",
            )
            saved = await self.optimization_repo.create(opt_result)
            iteration_results.append(saved)

            # 8. Check convergence
            converged = await self.optimization_agent.check_convergence(
                iteration_results, convergence_threshold
            )

        # Mark final iteration
        if iteration_results:
            final = iteration_results[-1]
            await self.optimization_repo.update(
                final.result_id,
                {"is_final_iteration": True, "convergence_achieved": converged},
            )

        final_score = initial_score or 0.0
        total_improvement = 0.0

        return {
            "campaign_id": campaign_id,
            "iterations_completed": iteration_count,
            "converged": converged,
            "final_performance": {"score": round(final_score, 4)},
            "total_improvement": round(total_improvement, 2),
            "variants_improved": sum(len(r.regenerated_variants) for r in iteration_results),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    async def _run_ab_test(
        self,
        campaign_id: str,
        variant_a_id: str,
        variant_b_id: str,
    ) -> dict[str, Any]:
        test = await self.ab_testing_svc.setup_ab_test(
            campaign_id, variant_a_id, variant_b_id, test_duration_hours=1
        )
        return {"test_id": test.test_id, "status": "created"}
