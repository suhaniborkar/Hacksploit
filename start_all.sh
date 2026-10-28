#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS — Full Platform Startup Script
# Seeds demo scenarios, starts FastAPI backend, KYC Form, and Admin Dashboard.
# ==============================================================================

set -e
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Trap Ctrl+C to cleanly terminate all background child processes
cleanup() {
    echo ""
    echo "🛑 Shutting down Project ARGUS platform services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "======================================================================"
echo "🛡️  PROJECT ARGUS — INITIALIZING PLATFORM"
echo "======================================================================"

# 1. Seed Demo Scenarios into Database
echo ""
echo "📦 Step 1/3: Seeding Realistic Fraud Scenarios into Database..."
python3 scripts/seed_demo_scenarios.py

# 2. Start FastAPI Backend on Port 8000
echo ""
echo "🚀 Step 2/3: Starting Modular Monolith Backend (Port 8000)..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "   Waiting for backend health check..."
until curl -s http://127.0.0.1:8000/health > /dev/null 2>&1 || curl -s http://127.0.0.1:8000/ > /dev/null 2>&1; do
    sleep 0.5
done
echo "   Backend online at http://127.0.0.1:8000"

# 3. Start Applicant KYC Onboarding Console (Port 5173)
echo ""
echo "💻 Step 3a: Launching Applicant KYC Console (Port 5173)..."
(cd kycform && npm run dev) &
KYC_PID=$!

# 4. Start Admin Intelligence Dashboard (Port 5174)
echo "💻 Step 3b: Launching Admin Intelligence Console (Port 5174)..."
(cd dashboard && npm run dev) &
DASHBOARD_PID=$!

sleep 2

echo ""
echo "======================================================================"
echo "✨ ALL SERVICES ARE LIVE & RUNNING!"
echo "======================================================================"
echo ""
echo "🔗 1. Applicant KYC Onboarding Console:"
echo "      http://localhost:5173"
echo "      -> Submit genuine ID documents or test webcam active liveness."
echo ""
echo "🔗 2. Admin Intelligence Dashboard (VeriYID):"
echo "      http://localhost:5174"
echo "      -> Login using pre-seeded staff credentials or 1-click role chips."
echo ""
echo "      Default Demo Accounts (Password: Argus<Role>2026!):"
echo "      • Admin:      admin@argus.internal      (ArgusAdmin2026!)"
echo "      • Analyst:    analyst@argus.internal    (ArgusAnalyst2026!)"
echo "      • Compliance: compliance@argus.internal (ArgusCompliance2026!)"
echo "      • Auditor:    auditor@argus.internal    (ArgusAuditor2026!)"
echo ""
echo "🔗 3. Backend API Documentation & OpenAPI Explorer:"
echo "      http://localhost:8000/docs"
echo ""
echo "💡 Press Ctrl+C at any time to stop all services."
echo "======================================================================"

# Keep running in foreground
wait
