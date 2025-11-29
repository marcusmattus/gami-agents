"""
Economy Management Agent - Tokenomics Simulation Engine
Controls XP to GAMI conversion rate using Monte Carlo simulation
"""
import numpy as np
from typing import Tuple, Dict, List
from datetime import datetime, timedelta
import json


class EconomySimulator:
    """
    Monte Carlo simulation for tokenomics management
    Predicts inflation and adjusts emission rates dynamically
    """
    
    def __init__(
        self,
        base_xp_to_gami_rate: float = 1000.0,
        deflation_adjustment: float = 0.10
    ):
        self.base_xp_to_gami_rate = base_xp_to_gami_rate
        self.current_xp_to_gami_rate = base_xp_to_gami_rate
        self.deflation_adjustment = deflation_adjustment
        self.simulation_history = []
        
    def run_monte_carlo_simulation(
        self,
        current_supply: float,
        adoption_rate: float,
        days: int = 30,
        iterations: int = 1000
    ) -> Dict:
        """
        Run Monte Carlo simulation to forecast inflation
        
        Args:
            current_supply: Current $GAMI token supply
            adoption_rate: Daily user adoption rate (percentage)
            days: Forecast period in days
            iterations: Number of simulation runs
            
        Returns:
            Dict with predicted inflation, supply forecast, and statistics
        """
        results = []
        
        for _ in range(iterations):
            supply = current_supply
            daily_supplies = [supply]
            
            for day in range(days):
                daily_adoption = np.random.normal(adoption_rate, adoption_rate * 0.2)
                daily_adoption = max(0, daily_adoption)
                
                base_daily_emission = supply * 0.001
                
                adoption_factor = 1 + (daily_adoption / 100)
                daily_emission = base_daily_emission * adoption_factor
                
                market_volatility = np.random.uniform(-0.05, 0.05)
                daily_emission *= (1 + market_volatility)
                
                supply += daily_emission
                daily_supplies.append(supply)
            
            final_supply = daily_supplies[-1]
            inflation = ((final_supply - current_supply) / current_supply) * 100
            results.append({
                'final_supply': final_supply,
                'inflation': inflation,
                'daily_supplies': daily_supplies
            })
        
        inflations = [r['inflation'] for r in results]
        final_supplies = [r['final_supply'] for r in results]
        
        predicted_inflation = np.mean(inflations)
        inflation_std = np.std(inflations)
        percentile_95 = np.percentile(inflations, 95)
        percentile_5 = np.percentile(inflations, 5)
        
        avg_daily_path = np.mean([r['daily_supplies'] for r in results], axis=0)
        
        simulation_result = {
            'predicted_inflation': predicted_inflation,
            'inflation_std': inflation_std,
            'confidence_interval_95': percentile_95,
            'confidence_interval_5': percentile_5,
            'mean_final_supply': np.mean(final_supplies),
            'current_supply': current_supply,
            'forecast_days': days,
            'iterations': iterations,
            'avg_supply_path': avg_daily_path.tolist(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.simulation_history.append(simulation_result)
        
        return simulation_result
    
    def evaluate_deflationary_protocol(self, predicted_inflation: float) -> Tuple[bool, float]:
        """
        Decision logic: Trigger deflationary protocol if inflation > 5%
        
        Returns:
            Tuple[trigger_protocol: bool, new_rate: float]
        """
        if predicted_inflation > 5.0:
            new_rate = self.current_xp_to_gami_rate * (1 + self.deflation_adjustment)
            return True, new_rate
        
        return False, self.current_xp_to_gami_rate
    
    def adjust_emission_rate(self, simulation_result: Dict) -> Dict:
        """
        Adjust XP-to-GAMI conversion rate based on simulation results
        
        Returns:
            Dict with decision details
        """
        predicted_inflation = simulation_result['predicted_inflation']
        
        trigger_deflation, new_rate = self.evaluate_deflationary_protocol(predicted_inflation)
        
        decision = {
            'timestamp': datetime.utcnow().isoformat(),
            'predicted_inflation': predicted_inflation,
            'trigger_deflationary_protocol': trigger_deflation,
            'previous_rate': self.current_xp_to_gami_rate,
            'new_rate': new_rate,
            'adjustment_percentage': ((new_rate - self.current_xp_to_gami_rate) / self.current_xp_to_gami_rate) * 100,
            'reason': f"Inflation {predicted_inflation:.2f}% {'exceeds' if trigger_deflation else 'within'} threshold"
        }
        
        if trigger_deflation:
            self.current_xp_to_gami_rate = new_rate
        
        return decision
    
    def get_current_emission_rate(self) -> float:
        """Return current XP-to-GAMI conversion rate"""
        return self.current_xp_to_gami_rate
    
    def calculate_gami_amount(self, xp_amount: int) -> float:
        """
        Calculate GAMI tokens for given XP amount
        Uses current emission rate
        """
        gami_amount = xp_amount / self.current_xp_to_gami_rate
        return round(gami_amount, 6)
    
    def get_simulation_history(self, limit: int = 10) -> List[Dict]:
        """Retrieve recent simulation history"""
        return self.simulation_history[-limit:]
    
    def forecast_supply_curve(
        self,
        current_supply: float,
        adoption_rates: List[float],
        days_per_scenario: int = 30
    ) -> Dict:
        """
        Run multiple scenarios with different adoption rates
        Useful for strategic planning
        """
        scenarios = {}
        
        for rate in adoption_rates:
            result = self.run_monte_carlo_simulation(
                current_supply=current_supply,
                adoption_rate=rate,
                days=days_per_scenario,
                iterations=500
            )
            
            scenarios[f"adoption_{rate}%"] = {
                'predicted_inflation': result['predicted_inflation'],
                'mean_final_supply': result['mean_final_supply'],
                'confidence_95': result['confidence_interval_95']
            }
        
        return scenarios
