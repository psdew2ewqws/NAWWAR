"""
Optimizer service — personalized energy savings recommendations.

Analyzes a consumer's bill history and consumption patterns to generate
actionable savings advice:
- Calculate the effective tariff tier distribution.
- Identify peak-usage periods (if time-of-use data is available).
- Estimate potential savings from tier migration.
- Generate localized Arabic tips via the SAVINGS_PROMPT template.
"""
import logging
from decimal import Decimal

from django.conf import settings

from apps.ai_engine.clients.anthropic_client import AnthropicClient
from apps.ai_engine.prompts.rag_prompts import SAVINGS_PROMPT, SYSTEM_PROMPT_AR
from apps.consumer.models import Subscription
from apps.consumer.selectors import (
    bill_list,
    subscription_get_by_number,
    tariff_get_active,
    tariff_periods_list,
)

logger = logging.getLogger(__name__)


class SavingsOptimizer:
    """Personalized energy savings analysis and recommendations."""

    def __init__(self):
        self.claude = AnthropicClient()
        self.emrc_tariffs = settings.EMRC_TARIFFS

    def analyze_consumption(self, *, subscription_id: int) -> dict:
        """
        Analyze consumption patterns from the last 3 bills.

        Args:
            subscription_id: ID of the Subscription record.

        Returns:
            Dict with consumption profile:
                subscription_id, subscriber_number, subscription_type,
                bills_analyzed, total_kwh, avg_monthly_kwh, avg_daily_kwh,
                peak_kwh, off_peak_kwh, peak_ratio, billing_days,
                avg_amount_fils, current_tier.
        """
        subscription = Subscription.objects.get(id=subscription_id)
        bills = list(bill_list(subscription=subscription, limit=3))

        if not bills:
            logger.warning("No bills found for subscription %d", subscription_id)
            return {
                'subscription_id': subscription_id,
                'subscriber_number': subscription.subscriber_number,
                'subscription_type': subscription.subscription_type,
                'bills_analyzed': 0,
                'total_kwh': 0,
                'avg_monthly_kwh': 0,
                'avg_daily_kwh': 0,
                'peak_kwh': 0,
                'off_peak_kwh': 0,
                'peak_ratio': 0,
                'billing_days': 0,
                'avg_amount_fils': 0,
                'current_tier': 1,
            }

        total_kwh = sum(float(b.total_kwh) for b in bills)
        total_peak = sum(float(b.peak_kwh) for b in bills)
        total_off_peak = sum(float(b.off_peak_kwh) for b in bills)
        total_amount = sum(b.total_amount_fils for b in bills)

        # Calculate total billing days
        total_days = 0
        for b in bills:
            delta = b.billing_period_end - b.billing_period_start
            total_days += max(delta.days, 1)

        num_bills = len(bills)
        avg_monthly_kwh = total_kwh / num_bills
        avg_daily_kwh = total_kwh / max(total_days, 1)
        avg_amount_fils = total_amount / num_bills
        peak_ratio = total_peak / total_kwh if total_kwh > 0 else 0

        # Determine current tariff tier based on average monthly consumption
        current_tier = self._determine_tier(
            kwh=avg_monthly_kwh,
            sector=subscription.subscription_type,
        )

        profile = {
            'subscription_id': subscription_id,
            'subscriber_number': subscription.subscriber_number,
            'subscription_type': subscription.subscription_type,
            'bills_analyzed': num_bills,
            'total_kwh': round(total_kwh, 2),
            'avg_monthly_kwh': round(avg_monthly_kwh, 2),
            'avg_daily_kwh': round(avg_daily_kwh, 2),
            'peak_kwh': round(total_peak, 2),
            'off_peak_kwh': round(total_off_peak, 2),
            'peak_ratio': round(peak_ratio, 4),
            'billing_days': total_days,
            'avg_amount_fils': round(avg_amount_fils),
            'current_tier': current_tier,
        }

        logger.info(
            "Consumption profile for %s: avg=%.0f kWh/month, tier=%d",
            subscription.subscriber_number, avg_monthly_kwh, current_tier,
        )

        return profile

    def calculate_savings(self, *, consumption_profile: dict) -> dict:
        """
        Calculate potential savings from load shifting (peak -> off-peak).

        Uses EMRC tariff tiers and TariffPeriod multipliers to estimate
        how much a consumer could save by shifting usage.

        Args:
            consumption_profile: Dict from analyze_consumption().

        Returns:
            Dict with:
                current_monthly_cost_fils, optimized_monthly_cost_fils,
                savings_fils, savings_jod, savings_percent,
                recommendations: list of recommendation dicts.
        """
        sector = consumption_profile.get('subscription_type', 'residential').upper()
        avg_kwh = consumption_profile.get('avg_monthly_kwh', 0)
        peak_ratio = consumption_profile.get('peak_ratio', 0)

        # Calculate current monthly cost using tiered tariff
        current_cost = self._calculate_tiered_cost(kwh=avg_kwh, sector=sector)

        # Apply peak multiplier to estimate real cost
        periods = list(tariff_periods_list())
        peak_multiplier = Decimal('1.0')
        off_peak_multiplier = Decimal('1.0')
        for period in periods:
            if period.is_peak:
                peak_multiplier = period.multiplier
            else:
                off_peak_multiplier = period.multiplier

        if peak_ratio > 0 and peak_multiplier > Decimal('1.0'):
            peak_cost_share = float(current_cost) * peak_ratio * float(peak_multiplier)
            off_peak_cost_share = float(current_cost) * (1 - peak_ratio) * float(off_peak_multiplier)
            current_cost_with_tou = peak_cost_share + off_peak_cost_share
        else:
            current_cost_with_tou = float(current_cost)

        # Optimized scenario: shift 30% of peak to off-peak
        shift_fraction = 0.30
        if peak_ratio > 0 and peak_multiplier > Decimal('1.0'):
            shifted_peak = peak_ratio * (1 - shift_fraction)
            shifted_off_peak = (1 - peak_ratio) + peak_ratio * shift_fraction
            optimized_peak_cost = float(current_cost) * shifted_peak * float(peak_multiplier)
            optimized_off_peak_cost = float(current_cost) * shifted_off_peak * float(off_peak_multiplier)
            optimized_cost = optimized_peak_cost + optimized_off_peak_cost
        else:
            optimized_cost = current_cost_with_tou

        # Also estimate savings from reducing one tier
        target_kwh = avg_kwh * 0.85  # 15% reduction target
        tier_reduction_cost = self._calculate_tiered_cost(kwh=target_kwh, sector=sector)
        tier_savings = float(current_cost) - float(tier_reduction_cost)

        total_savings = max(current_cost_with_tou - optimized_cost + tier_savings, 0)
        savings_percent = (total_savings / current_cost_with_tou * 100) if current_cost_with_tou > 0 else 0

        recommendations = self._build_recommendations(
            consumption_profile=consumption_profile,
            tier_savings_fils=round(tier_savings),
            tou_savings_fils=round(current_cost_with_tou - optimized_cost),
        )

        result = {
            'current_monthly_cost_fils': round(current_cost_with_tou),
            'optimized_monthly_cost_fils': round(current_cost_with_tou - total_savings),
            'savings_fils': round(total_savings),
            'savings_jod': round(total_savings / 1000, 3),
            'savings_percent': round(savings_percent, 1),
            'recommendations': recommendations,
        }

        logger.info(
            "Savings calculation: current=%d fils, savings=%d fils (%.1f%%)",
            result['current_monthly_cost_fils'],
            result['savings_fils'],
            result['savings_percent'],
        )

        return result

    async def generate_recommendations(
        self,
        *,
        consumption_profile: dict,
        savings: dict,
        language: str = 'ar',
    ) -> str:
        """
        Generate personalized Arabic recommendations using Claude.

        Args:
            consumption_profile: Dict from analyze_consumption().
            savings: Dict from calculate_savings().
            language: Response language (default: Arabic).

        Returns:
            Formatted Arabic text with specific appliance recommendations.
        """
        # Build the context from savings data
        context_parts = []
        for rec in savings.get('recommendations', []):
            context_parts.append(f"- {rec['title_ar']}: {rec['description_ar']}")

        context = '\n'.join(context_parts) if context_parts else 'لا توجد بيانات إضافية'

        prompt = SAVINGS_PROMPT.format(
            consumption_kwh=consumption_profile.get('avg_monthly_kwh', 0),
            current_tier=consumption_profile.get('current_tier', 1),
            total_amount_fils=consumption_profile.get('avg_amount_fils', 0),
            context=context,
        )

        response = await self.claude.chat(
            messages=[{'role': 'user', 'content': prompt}],
            system_prompt=SYSTEM_PROMPT_AR,
        )

        logger.info("Generated AI recommendations: %d chars", len(response))
        return response

    async def full_analysis(self, *, subscription_id: int) -> dict:
        """
        Run the complete savings analysis pipeline.

        Args:
            subscription_id: ID of the Subscription record.

        Returns:
            Dict with:
                consumption_profile, savings, ai_recommendations.
        """
        logger.info("Starting full savings analysis for subscription %d", subscription_id)

        # Step 1: Analyze consumption
        profile = self.analyze_consumption(subscription_id=subscription_id)

        if profile['bills_analyzed'] == 0:
            return {
                'consumption_profile': profile,
                'savings': {
                    'current_monthly_cost_fils': 0,
                    'optimized_monthly_cost_fils': 0,
                    'savings_fils': 0,
                    'savings_jod': 0,
                    'savings_percent': 0,
                    'recommendations': [],
                },
                'ai_recommendations': 'لا تتوفر بيانات استهلاك كافية لإجراء التحليل.',
            }

        # Step 2: Calculate savings
        savings = self.calculate_savings(consumption_profile=profile)

        # Step 3: Generate AI recommendations
        ai_text = await self.generate_recommendations(
            consumption_profile=profile,
            savings=savings,
        )

        return {
            'consumption_profile': profile,
            'savings': savings,
            'ai_recommendations': ai_text,
        }

    def _determine_tier(self, *, kwh: float, sector: str) -> int:
        """Determine the highest tariff tier reached for given consumption."""
        sector_key = sector.upper()
        tiers = self.emrc_tariffs.get(sector_key, self.emrc_tariffs['RESIDENTIAL'])

        current_tier = 1
        for tier in tiers:
            if kwh >= tier['min_kwh']:
                current_tier = tier['tier']

        return current_tier

    def _calculate_tiered_cost(self, *, kwh: float, sector: str) -> float:
        """Calculate the total cost using tiered tariff rates."""
        tiers = self.emrc_tariffs.get(sector, self.emrc_tariffs['RESIDENTIAL'])
        remaining = kwh
        total_cost = 0.0

        for tier in tiers:
            if remaining <= 0:
                break

            tier_range = tier['max_kwh'] - tier['min_kwh']
            if tier['min_kwh'] == 0:
                tier_range = tier['max_kwh']

            consumed_in_tier = min(remaining, tier_range)
            total_cost += consumed_in_tier * tier['rate_fils']
            remaining -= consumed_in_tier

        return total_cost

    @staticmethod
    def _build_recommendations(
        *,
        consumption_profile: dict,
        tier_savings_fils: int,
        tou_savings_fils: int,
    ) -> list[dict]:
        """Build a list of actionable savings recommendations."""
        recommendations = []
        avg_kwh = consumption_profile.get('avg_monthly_kwh', 0)
        peak_ratio = consumption_profile.get('peak_ratio', 0)

        # Load shifting recommendation
        if peak_ratio > 0.4 and tou_savings_fils > 0:
            recommendations.append({
                'type': 'load_shifting',
                'title': 'Shift appliances to off-peak hours',
                'title_ar': 'نقل تشغيل الأجهزة لساعات خارج الذروة',
                'description': f'Move washing, dishwasher, and water heater usage to off-peak hours. Potential saving: {tou_savings_fils} fils/month.',
                'description_ar': f'انقل تشغيل الغسالة وسخان الماء إلى ساعات خارج الذروة. التوفير المتوقع: {tou_savings_fils} فلس/شهر.',
                'potential_savings_fils': tou_savings_fils,
            })

        # Tier reduction recommendation
        if tier_savings_fils > 0:
            recommendations.append({
                'type': 'tier_reduction',
                'title': 'Reduce consumption to reach a lower tier',
                'title_ar': 'تخفيض الاستهلاك للوصول إلى شريحة أقل',
                'description': f'Reducing consumption by 15% could save {tier_savings_fils} fils/month by moving to a lower tariff tier.',
                'description_ar': f'تخفيض الاستهلاك بنسبة ١٥٪ يوفر {tier_savings_fils} فلس/شهر بالانتقال لشريحة أقل.',
                'potential_savings_fils': tier_savings_fils,
            })

        # AC optimization (for high consumers)
        if avg_kwh > 500:
            recommendations.append({
                'type': 'ac_optimization',
                'title': 'Optimize air conditioning usage',
                'title_ar': 'تحسين استخدام التكييف',
                'description': 'Set AC to 24°C instead of lower temperatures. Each degree saves ~6% on cooling costs.',
                'description_ar': 'اضبط التكييف على ٢٤ درجة بدلاً من درجات أقل. كل درجة توفر ~٦٪ من تكلفة التبريد.',
                'potential_savings_fils': round(avg_kwh * 0.06 * 86),
            })

        # Lighting upgrade
        if avg_kwh > 300:
            recommendations.append({
                'type': 'lighting',
                'title': 'Switch to LED lighting',
                'title_ar': 'التحول إلى إضاءة LED',
                'description': 'LED bulbs use 75% less energy than incandescent bulbs.',
                'description_ar': 'مصابيح LED توفر ٧٥٪ من استهلاك الإضاءة مقارنة بالمصابيح التقليدية.',
                'potential_savings_fils': round(avg_kwh * 0.10 * 33),
            })

        # Water heater timer
        recommendations.append({
            'type': 'water_heater',
            'title': 'Use a water heater timer',
            'title_ar': 'استخدام مؤقت لسخان الماء',
            'description': 'A timer prevents the water heater from running all day. Typical saving: 15-20% on water heating.',
            'description_ar': 'مؤقت السخان يمنع تشغيله طوال اليوم. التوفير النموذجي: ١٥-٢٠٪ من استهلاك التسخين.',
            'potential_savings_fils': round(avg_kwh * 0.05 * 33),
        })

        return recommendations
