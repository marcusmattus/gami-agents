"""
Test script to demonstrate Gami Protocol agents
Run after starting all services
"""
import requests
import json
from datetime import datetime, timedelta
from uuid import uuid4

BASE_URLS = {
    'quest': 'http://localhost:8001',
    'economy': 'http://localhost:8002',
    'security': 'http://localhost:8003'
}


def test_quest_generation():
    """Test Quest Generation Agent"""
    print("\n" + "="*60)
    print("TESTING QUEST GENERATION AGENT")
    print("="*60)
    
    # Test user profile with low reputation (should get easy quest)
    user_profile_low = {
        "user_identity": {
            "wallet_id": "0xABC123",
            "xp_balance": 100,
            "reputation_score": 15.0
        },
        "recent_events": [
            {
                "user_id": "0xABC123",
                "source": "web3",
                "action_type": "stake_tokens",
                "meta_data": {"xp_earned": 50}
            }
        ],
        "total_quests_completed": 1,
        "average_completion_time": 3600.0
    }
    
    print("\n1. Generating quest for LOW reputation user (< 20)...")
    response = requests.post(
        f"{BASE_URLS['quest']}/generate-quest",
        json=user_profile_low
    )
    
    if response.status_code == 200:
        quest = response.json()
        print(f"✓ Quest generated!")
        print(f"  - Difficulty: {quest['difficulty_rating']} (should be 1-3 for low rep)")
        print(f"  - XP Reward: {quest['reward_xp']}")
        print(f"  - GAMI Reward: {quest['reward_gami']}")
        print(f"  - Criteria: {json.dumps(quest['completion_criteria'], indent=2)}")
    else:
        print(f"✗ Failed: {response.text}")
    
    # Test user with high reputation
    user_profile_high = {
        "user_identity": {
            "wallet_id": "0xDEF456",
            "xp_balance": 5000,
            "reputation_score": 85.0
        },
        "recent_events": [],
        "total_quests_completed": 20,
        "average_completion_time": 1800.0
    }
    
    print("\n2. Generating quest for HIGH reputation user...")
    response = requests.post(
        f"{BASE_URLS['quest']}/generate-quest",
        json=user_profile_high
    )
    
    if response.status_code == 200:
        quest = response.json()
        print(f"✓ Quest generated!")
        print(f"  - Difficulty: {quest['difficulty_rating']}")
        print(f"  - XP Reward: {quest['reward_xp']}")
        print(f"  - GAMI Reward: {quest['reward_gami']}")


def test_economy_management():
    """Test Economy Management Agent"""
    print("\n" + "="*60)
    print("TESTING ECONOMY MANAGEMENT AGENT")
    print("="*60)
    
    print("\n1. Getting current emission rate...")
    response = requests.get(f"{BASE_URLS['economy']}/get-current-emission-rate")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Current Rate: {data['xp_to_gami_rate']}")
        print(f"  - Description: {data['description']}")
    else:
        print(f"✗ Failed: {response.text}")
    
    print("\n2. Running Monte Carlo simulation (LOW adoption - should NOT trigger deflation)...")
    simulation_low = {
        "current_supply": 1000000,
        "adoption_rate": 2.0,
        "days": 30,
        "iterations": 1000
    }
    
    response = requests.post(
        f"{BASE_URLS['economy']}/run-simulation",
        json=simulation_low
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Simulation complete!")
        print(f"  - Predicted Inflation: {result['simulation_result']['predicted_inflation']:.2f}%")
        print(f"  - Deflationary Protocol: {result['adjustment_decision']['trigger_deflationary_protocol']}")
        print(f"  - New Rate: {result['adjustment_decision']['new_rate']}")
    else:
        print(f"✗ Failed: {response.text}")
    
    print("\n3. Running Monte Carlo simulation (HIGH adoption - SHOULD trigger deflation)...")
    simulation_high = {
        "current_supply": 1000000,
        "adoption_rate": 15.0,
        "days": 30,
        "iterations": 1000
    }
    
    response = requests.post(
        f"{BASE_URLS['economy']}/run-simulation",
        json=simulation_high
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Simulation complete!")
        print(f"  - Predicted Inflation: {result['simulation_result']['predicted_inflation']:.2f}%")
        print(f"  - Deflationary Protocol: {result['adjustment_decision']['trigger_deflationary_protocol']}")
        print(f"  - Previous Rate: {result['adjustment_decision']['previous_rate']}")
        print(f"  - New Rate: {result['adjustment_decision']['new_rate']}")
        print(f"  - Adjustment: {result['adjustment_decision']['adjustment_percentage']:.2f}%")
    else:
        print(f"✗ Failed: {response.text}")
    
    print("\n4. Converting XP to GAMI...")
    conversion = {"xp_amount": 5000}
    
    response = requests.post(
        f"{BASE_URLS['economy']}/convert-xp-to-gami",
        json=conversion
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Conversion complete!")
        print(f"  - {result['xp_amount']} XP = {result['gami_amount']} GAMI")
        print(f"  - Rate: {result['conversion_rate']}")
    else:
        print(f"✗ Failed: {response.text}")


def test_security_agent():
    """Test Security Agent"""
    print("\n" + "="*60)
    print("TESTING SECURITY AGENT (FRAUD DETECTION)")
    print("="*60)
    
    print("\n1. Training fraud detection model...")
    response = requests.post(f"{BASE_URLS['security']}/train-model")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Model training initiated")
        print(f"  - Status: {result['status']}")
    else:
        print(f"✗ Failed: {response.text}")
    
    print("\n2. Ingesting NORMAL user events...")
    normal_events = [
        {
            "user_id": "0xNORMAL123",
            "source": "web3",
            "action_type": "complete_quest",
            "meta_data": {"xp_earned": 100}
        },
        {
            "user_id": "0xNORMAL123",
            "source": "web2",
            "action_type": "social_share",
            "meta_data": {"xp_earned": 50}
        }
    ]
    
    response = requests.post(
        f"{BASE_URLS['security']}/ingest-events",
        json=normal_events
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Events ingested: {result['events_ingested']}")
    else:
        print(f"✗ Failed: {response.text}")
    
    print("\n3. Ingesting SUSPICIOUS user events (Sybil-like behavior)...")
    # Generate high-frequency suspicious events
    suspicious_events = []
    base_time = datetime.utcnow()
    
    for i in range(50):
        suspicious_events.append({
            "user_id": "0xSUSPICIOUS999",
            "source": "web3",
            "action_type": "bot_action",
            "meta_data": {"xp_earned": 1000},
            "timestamp": (base_time + timedelta(seconds=i*5)).isoformat()
        })
    
    response = requests.post(
        f"{BASE_URLS['security']}/ingest-events",
        json=suspicious_events
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Suspicious events ingested: {result['events_ingested']}")
    else:
        print(f"✗ Failed: {response.text}")
    
    print("\n4. Detecting Sybil cluster...")
    response = requests.post(
        f"{BASE_URLS['security']}/detect-sybil-cluster?lookback_hours=24"
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Sybil detection complete!")
        print(f"  - Suspicious users found: {result['count']}")
        if result['suspicious_users']:
            print(f"  - Users: {result['suspicious_users']}")
    else:
        print(f"✗ Failed: {response.text}")
    
    print("\n5. Getting fraud alerts...")
    response = requests.get(f"{BASE_URLS['security']}/fraud-alerts?limit=5")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Retrieved {result['count']} alerts")
        for alert in result['alerts'][:3]:
            print(f"  - User: {alert['user_id']}")
            print(f"    Reason: {alert['reason']}")
            print(f"    Action: {alert['action_taken']}")
    else:
        print(f"✗ Failed: {response.text}")


def test_health_checks():
    """Test all service health endpoints"""
    print("\n" + "="*60)
    print("HEALTH CHECKS")
    print("="*60)
    
    for service, url in BASE_URLS.items():
        response = requests.get(f"{url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ {service.upper()} Agent: {data['status']}")
        else:
            print(f"✗ {service.upper()} Agent: UNHEALTHY")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("GAMI PROTOCOL - AGENT TEST SUITE")
    print("="*60)
    
    try:
        test_health_checks()
        test_quest_generation()
        test_economy_management()
        test_security_agent()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED!")
        print("="*60 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to services.")
        print("Make sure all agents are running:")
        print("  - Quest Agent: http://localhost:8001")
        print("  - Economy Agent: http://localhost:8002")
        print("  - Security Agent: http://localhost:8003")
        print("\nStart with: docker-compose up -d")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
