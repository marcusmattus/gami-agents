"""
Economy Management Agent - FastAPI Microservice
Manages tokenomics and emission rates using Monte Carlo simulation
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import redis_client
from simulation_engine import EconomySimulator

app = FastAPI(
    title="Economy Management Agent",
    description="Gami Protocol Tokenomics Management Service",
    version="1.0.0"
)

economy_simulator = EconomySimulator(
    base_xp_to_gami_rate=1000.0,
    deflation_adjustment=0.10
)


class SimulationRequest(BaseModel):
    """Request model for running simulations"""
    current_supply: float = Field(..., gt=0, description="Current $GAMI supply")
    adoption_rate: float = Field(..., ge=0, le=100, description="Daily adoption rate %")
    days: int = Field(default=30, ge=1, le=365, description="Forecast period")
    iterations: int = Field(default=1000, ge=100, le=10000, description="Simulation iterations")


class ConversionRequest(BaseModel):
    """Request for XP to GAMI conversion"""
    xp_amount: int = Field(..., gt=0, description="XP amount to convert")


@app.on_event("startup")
async def startup_event():
    """Initialize economy state on startup"""
    try:
        redis_client.set("economy:xp_to_gami_rate", economy_simulator.get_current_emission_rate())
        redis_client.set("economy:last_simulation", "")
        print("Economy Management Agent initialized")
    except Exception as e:
        print(f"Redis initialization warning: {e}")


@app.post("/run-simulation")
async def run_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """
    Run Monte Carlo simulation to forecast inflation
    Automatically triggers deflationary protocol if inflation > 5%
    """
    try:
        result = economy_simulator.run_monte_carlo_simulation(
            current_supply=request.current_supply,
            adoption_rate=request.adoption_rate,
            days=request.days,
            iterations=request.iterations
        )
        
        decision = economy_simulator.adjust_emission_rate(result)
        
        try:
            redis_client.set("economy:xp_to_gami_rate", economy_simulator.get_current_emission_rate())
            redis_client.set("economy:last_simulation", str(result))
        except Exception as e:
            print(f"Redis cache warning: {e}")
        
        return {
            "simulation_result": result,
            "adjustment_decision": decision,
            "current_emission_rate": economy_simulator.get_current_emission_rate()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@app.get("/get-current-emission-rate")
async def get_current_emission_rate():
    """
    Get current XP-to-GAMI conversion rate
    Called by Reward Orchestrator before minting tokens
    """
    try:
        rate = economy_simulator.get_current_emission_rate()
        
        try:
            cached_rate = redis_client.get("economy:xp_to_gami_rate")
            if cached_rate:
                rate = float(cached_rate)
        except Exception as e:
            print(f"Redis read warning: {e}")
        
        return {
            "xp_to_gami_rate": rate,
            "description": f"1 GAMI = {rate} XP",
            "inverse_rate": round(1 / rate, 6) if rate > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rate retrieval failed: {str(e)}")


@app.post("/convert-xp-to-gami")
async def convert_xp_to_gami(request: ConversionRequest):
    """
    Convert XP amount to GAMI tokens
    Uses current emission rate
    """
    try:
        gami_amount = economy_simulator.calculate_gami_amount(request.xp_amount)
        
        return {
            "xp_amount": request.xp_amount,
            "gami_amount": gami_amount,
            "conversion_rate": economy_simulator.get_current_emission_rate(),
            "timestamp": economy_simulator.simulation_history[-1]['timestamp'] if economy_simulator.simulation_history else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.post("/forecast-scenarios")
async def forecast_scenarios(
    current_supply: float,
    adoption_rates: List[float] = [1.0, 3.0, 5.0, 10.0],
    days_per_scenario: int = 30
):
    """
    Run multiple forecast scenarios with different adoption rates
    Useful for strategic planning
    """
    try:
        scenarios = economy_simulator.forecast_supply_curve(
            current_supply=current_supply,
            adoption_rates=adoption_rates,
            days_per_scenario=days_per_scenario
        )
        
        return {
            "scenarios": scenarios,
            "current_emission_rate": economy_simulator.get_current_emission_rate()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario forecasting failed: {str(e)}")


@app.get("/simulation-history")
async def get_simulation_history(limit: int = 10):
    """Retrieve recent simulation history"""
    try:
        history = economy_simulator.get_simulation_history(limit=limit)
        return {"history": history, "count": len(history)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History retrieval failed: {str(e)}")


@app.post("/manual-rate-adjustment")
async def manual_rate_adjustment(new_rate: float):
    """
    Manual override for emission rate (admin only)
    Use with caution
    """
    try:
        old_rate = economy_simulator.get_current_emission_rate()
        economy_simulator.current_xp_to_gami_rate = new_rate
        
        try:
            redis_client.set("economy:xp_to_gami_rate", new_rate)
        except Exception as e:
            print(f"Redis update warning: {e}")
        
        return {
            "status": "success",
            "old_rate": old_rate,
            "new_rate": new_rate,
            "change_percentage": ((new_rate - old_rate) / old_rate) * 100
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rate adjustment failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "economy_management_agent",
        "current_rate": economy_simulator.get_current_emission_rate()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
