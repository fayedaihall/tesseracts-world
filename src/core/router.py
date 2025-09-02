import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from ..models.core import (
    Quote, MovementRequest, ServiceType, Priority, Location
)
from ..adapters.base import ProviderAdapter

logger = logging.getLogger(__name__)

class RouteOptimizer:
    """Intelligent routing engine for selecting optimal providers and routes"""
    
    def __init__(self, providers: List[ProviderAdapter]):
        self.providers = providers
        self.weights = {
            "cost": 0.3,
            "time": 0.4,
            "reliability": 0.2,
            "quality": 0.1
        }
    
    async def get_optimal_quotes(
        self, 
        request: MovementRequest, 
        max_quotes: int = 5
    ) -> List[Quote]:
        """Get quotes from all suitable providers and rank them"""
        
        # Filter providers by service type and coverage
        suitable_providers = self._filter_suitable_providers(request)
        
        if not suitable_providers:
            logger.warning(f"No suitable providers found for {request.service_type}")
            return []
        
        # Get quotes from all suitable providers concurrently
        quote_tasks = [
            self._get_provider_quote(provider, request) 
            for provider in suitable_providers
        ]
        
        quote_results = await asyncio.gather(*quote_tasks, return_exceptions=True)
        
        # Filter out failed quotes and exceptions
        valid_quotes = [
            quote for quote in quote_results 
            if isinstance(quote, Quote) and quote is not None
        ]
        
        if not valid_quotes:
            logger.warning("No valid quotes received from any provider")
            return []
        
        # Score and rank quotes
        scored_quotes = [
            (quote, self._calculate_quote_score(quote, request))
            for quote in valid_quotes
        ]
        
        # Sort by score (higher is better)
        scored_quotes.sort(key=lambda x: x[1], reverse=True)
        
        # Return top quotes
        return [quote for quote, score in scored_quotes[:max_quotes]]
    
    def _filter_suitable_providers(self, request: MovementRequest) -> List[ProviderAdapter]:
        """Filter providers that can handle this request"""
        suitable = []
        
        for provider in self.providers:
            # Check service type support
            if request.service_type not in provider.supported_service_types:
                continue
            
            # Check geographic coverage (simplified)
            # In a real implementation, this would check specific coordinates
            coverage_areas = provider.coverage_areas
            if "global" in coverage_areas or "local" in coverage_areas:
                suitable.append(provider)
            
        return suitable
    
    async def _get_provider_quote(
        self, 
        provider: ProviderAdapter, 
        request: MovementRequest
    ) -> Optional[Quote]:
        """Get quote from a single provider with error handling"""
        try:
            quote = await provider.get_quote(request)
            if quote:
                logger.info(f"Got quote from {provider.provider_id}: ${quote.estimated_cost}")
            return quote
        except Exception as e:
            logger.error(f"Error getting quote from {provider.provider_id}: {e}")
            return None
    
    def _calculate_quote_score(self, quote: Quote, request: MovementRequest) -> float:
        """Calculate a normalized score for a quote based on multiple factors"""
        
        # Normalize cost (lower is better, 0-1 scale)
        cost_score = self._normalize_cost_score(quote.estimated_cost)
        
        # Normalize time (faster is better, 0-1 scale)
        time_score = self._normalize_time_score(
            quote.estimated_pickup_time, 
            quote.estimated_delivery_time,
            request.requested_pickup_time
        )
        
        # Provider reliability score (based on confidence and past performance)
        reliability_score = quote.confidence_score
        
        # Quality score (based on worker rating if available)
        quality_score = self._calculate_quality_score(quote)
        
        # Priority adjustments
        priority_adjustment = self._get_priority_adjustment(request.priority, quote)
        
        # Calculate weighted score
        total_score = (
            self.weights["cost"] * cost_score +
            self.weights["time"] * time_score +
            self.weights["reliability"] * reliability_score +
            self.weights["quality"] * quality_score
        ) * priority_adjustment
        
        logger.debug(
            f"Quote {quote.quote_id} scores: "
            f"cost={cost_score:.2f}, time={time_score:.2f}, "
            f"reliability={reliability_score:.2f}, quality={quality_score:.2f}, "
            f"total={total_score:.2f}"
        )
        
        return total_score
    
    def _normalize_cost_score(self, cost: Decimal) -> float:
        """Normalize cost to 0-1 score (lower cost = higher score)"""
        # Simple normalization - in production, this would use historical data
        max_reasonable_cost = Decimal("100.00")
        min_reasonable_cost = Decimal("5.00")
        
        if cost <= min_reasonable_cost:
            return 1.0
        elif cost >= max_reasonable_cost:
            return 0.1
        else:
            # Linear normalization (inverted so lower cost = higher score)
            normalized = 1.0 - float((cost - min_reasonable_cost) / (max_reasonable_cost - min_reasonable_cost))
            return max(0.1, normalized)
    
    def _normalize_time_score(
        self, 
        pickup_time: datetime, 
        delivery_time: datetime,
        requested_pickup: Optional[datetime]
    ) -> float:
        """Normalize timing to 0-1 score (faster = higher score)"""
        
        current_time = datetime.utcnow()
        
        # Calculate pickup delay
        pickup_delay_minutes = (pickup_time - current_time).total_seconds() / 60
        
        # Calculate total duration
        total_duration_minutes = (delivery_time - pickup_time).total_seconds() / 60
        
        # Score pickup timing (sooner is better, but not too soon)
        if requested_pickup:
            pickup_diff = abs((pickup_time - requested_pickup).total_seconds() / 60)
            pickup_score = max(0, 1.0 - pickup_diff / 60)  # Penalize if more than 1 hour off
        else:
            # If no specific time requested, prefer quick pickup (within reason)
            pickup_score = max(0.1, 1.0 - pickup_delay_minutes / 60)
        
        # Score duration (faster delivery is better)
        max_reasonable_duration = 120  # 2 hours
        duration_score = max(0.1, 1.0 - total_duration_minutes / max_reasonable_duration)
        
        # Combine pickup and duration scores
        return (pickup_score + duration_score) / 2
    
    def _calculate_quality_score(self, quote: Quote) -> float:
        """Calculate quality score based on worker and provider info"""
        
        base_score = 0.7  # Default quality score
        
        if quote.worker_info and quote.worker_info.rating:
            # Convert 5-star rating to 0-1 score
            rating_score = quote.worker_info.rating / 5.0
            return rating_score
        
        return base_score
    
    def _get_priority_adjustment(self, priority: Priority, quote: Quote) -> float:
        """Adjust score based on request priority and quote characteristics"""
        
        if priority == Priority.URGENT:
            # For urgent requests, heavily favor quick pickup
            current_time = datetime.utcnow()
            pickup_delay = (quote.estimated_pickup_time - current_time).total_seconds() / 60
            
            if pickup_delay <= 10:  # Very quick pickup
                return 1.3
            elif pickup_delay <= 20:  # Reasonably quick
                return 1.1
            else:  # Too slow for urgent
                return 0.7
        
        elif priority == Priority.HIGH:
            # Favor reliability and quality
            return 1.0 + (quote.confidence_score - 0.5) * 0.2
        
        elif priority == Priority.LOW:
            # Favor cost efficiency
            return 1.0  # Cost is already weighted in the base calculation
        
        return 1.0  # Normal priority
    
    async def optimize_multi_stop_route(
        self, 
        stops: List[Location], 
        service_type: ServiceType
    ) -> List[Tuple[Location, Location]]:
        """Optimize route for multiple stops (simplified TSP)"""
        
        if len(stops) <= 2:
            return [(stops[0], stops[-1])]
        
        # Simple nearest neighbor algorithm for demonstration
        # In production, this would use more sophisticated routing algorithms
        
        optimized_route = []
        remaining_stops = stops[1:-1]  # Exclude start and end
        current_location = stops[0]
        
        while remaining_stops:
            # Find nearest unvisited stop
            nearest_stop = min(
                remaining_stops,
                key=lambda stop: self._calculate_distance(current_location, stop)
            )
            
            optimized_route.append((current_location, nearest_stop))
            current_location = nearest_stop
            remaining_stops.remove(nearest_stop)
        
        # Add final leg to destination
        optimized_route.append((current_location, stops[-1]))
        
        return optimized_route
    
    def _calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """Calculate approximate distance between two locations in km"""
        lat_diff = abs(loc1.latitude - loc2.latitude)
        lng_diff = abs(loc1.longitude - loc2.longitude)
        return ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111  # Rough conversion to km
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Update scoring weights for different factors"""
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")
        
        self.weights.update(new_weights)
        logger.info(f"Updated routing weights: {self.weights}")
    
    async def get_provider_health_status(self) -> Dict[str, bool]:
        """Check health status of all providers"""
        health_tasks = [
            provider.health_check() for provider in self.providers
        ]
        
        health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        return {
            provider.provider_id: result if isinstance(result, bool) else False
            for provider, result in zip(self.providers, health_results)
        }
