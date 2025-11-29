#!/bin/bash

# Gami Protocol - Agent Startup Script

echo "=========================================="
echo "   GAMI PROTOCOL - AGENT DEPLOYMENT"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✓ Docker and Docker Compose are installed"
echo ""

# Start services
echo "Starting Gami Protocol services..."
echo ""

docker-compose up -d

echo ""
echo "Waiting for services to initialize..."
sleep 10

# Check service health
echo ""
echo "=========================================="
echo "   SERVICE HEALTH CHECK"
echo "=========================================="
echo ""

check_service() {
    local name=$1
    local port=$2
    
    if curl -s http://localhost:$port/health > /dev/null 2>&1; then
        echo "✓ $name Agent (Port $port): HEALTHY"
    else
        echo "✗ $name Agent (Port $port): UNHEALTHY"
    fi
}

check_service "Quest Generation" 8001
check_service "Economy Management" 8002
check_service "Security" 8003

echo ""
echo "=========================================="
echo "   AGENT ENDPOINTS"
echo "=========================================="
echo ""
echo "Quest Generation Agent:"
echo "  http://localhost:8001"
echo "  http://localhost:8001/docs (Swagger UI)"
echo ""
echo "Economy Management Agent:"
echo "  http://localhost:8002"
echo "  http://localhost:8002/docs (Swagger UI)"
echo ""
echo "Security Agent:"
echo "  http://localhost:8003"
echo "  http://localhost:8003/docs (Swagger UI)"
echo ""
echo "Supervisor MCP Server:"
echo "  SSE endpoint: http://localhost:8800/mcp"
echo "  Transport: ${MCP_TRANSPORT:-sse}"
echo ""
echo "=========================================="
echo "   DATABASE CONNECTIONS"
echo "=========================================="
echo ""
echo "PostgreSQL: localhost:5432"
echo "  Database: gami_protocol"
echo "  User: gami"
echo "  Password: gami"
echo ""
echo "Redis: localhost:6379"
echo ""
echo "=========================================="
echo "   TESTING"
echo "=========================================="
echo ""
echo "Run test suite with:"
echo "  python test_agents.py"
echo ""
echo "View logs with:"
echo "  docker-compose logs -f"
echo ""
echo "Stop services with:"
echo "  docker-compose down"
echo ""
echo "=========================================="
echo "   DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
