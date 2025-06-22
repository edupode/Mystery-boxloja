#!/bin/bash

# DEPLOY HELPER SCRIPTS - MYSTERY BOX STORE

echo "🚀 Mystery Box Store - Deploy Helper Scripts"
echo "============================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists "node"; then
        print_error "Node.js is not installed"
        exit 1
    fi
    
    if ! command_exists "python3"; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    if ! command_exists "git"; then
        print_error "Git is not installed"
        exit 1
    fi
    
    print_success "All prerequisites are installed"
}

# Build frontend for production
build_frontend() {
    print_status "Building frontend for production..."
    cd frontend
    
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        if command_exists "yarn"; then
            yarn install
        else
            npm install
        fi
    fi
    
    print_status "Creating production build..."
    if command_exists "yarn"; then
        yarn build
    else
        npm run build
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Frontend build completed successfully"
    else
        print_error "Frontend build failed"
        exit 1
    fi
    
    cd ..
}

# Test backend locally
test_backend() {
    print_status "Testing backend locally..."
    cd backend
    
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    pip install -r requirements.txt
    
    print_status "Running backend tests..."
    python -m pytest tests/ -v || print_warning "No tests found or tests failed"
    
    deactivate
    cd ..
}

# Validate environment files
validate_env() {
    print_status "Validating environment configuration..."
    
    # Check backend env
    if [ ! -f "backend/.env" ]; then
        print_warning "Backend .env file not found. Using example..."
        if [ -f "backend/.env.production.example" ]; then
            cp backend/.env.production.example backend/.env
            print_warning "Please edit backend/.env with your actual values"
        fi
    fi
    
    # Check frontend env
    if [ ! -f "frontend/.env" ]; then
        print_warning "Frontend .env file not found. Using example..."
        if [ -f "frontend/.env.production.example" ]; then
            cp frontend/.env.production.example frontend/.env
            print_warning "Please edit frontend/.env with your actual values"
        fi
    fi
    
    print_success "Environment validation completed"
}

# Deploy to Vercel (frontend)
deploy_frontend() {
    print_status "Deploying frontend to Vercel..."
    
    if ! command_exists "vercel"; then
        print_error "Vercel CLI not installed. Install with: npm i -g vercel"
        exit 1
    fi
    
    cd frontend
    vercel --prod
    cd ..
    
    print_success "Frontend deployment to Vercel completed"
}

# Show deploy checklist
show_checklist() {
    echo
    print_status "PRE-DEPLOYMENT CHECKLIST"
    echo "========================="
    echo "□ MongoDB Atlas cluster created and configured"
    echo "□ Render.com account created"
    echo "□ Vercel account created"
    echo "□ Google OAuth configured for production domains"
    echo "□ Stripe keys configured (test or production)"
    echo "□ Resend API key configured"
    echo "□ Domain verified in Resend (if using custom domain)"
    echo "□ All environment variables set in production"
    echo "□ CORS origins configured correctly"
    echo "□ JWT secret is strong and secure"
    echo "□ Admin email configured"
    echo
    print_status "DEPLOYMENT STEPS"
    echo "================"
    echo "1. Deploy backend to Render.com first"
    echo "2. Copy backend URL to frontend environment"
    echo "3. Deploy frontend to Vercel"
    echo "4. Update Google OAuth with production URLs"
    echo "5. Test all functionality in production"
    echo
}

# Main menu
show_menu() {
    echo
    echo "Select an option:"
    echo "1. Check prerequisites"
    echo "2. Validate environment files"
    echo "3. Build frontend"
    echo "4. Test backend"
    echo "5. Deploy frontend to Vercel (requires Vercel CLI)"
    echo "6. Show deployment checklist"
    echo "7. Exit"
    echo
}

# Main script
main() {
    while true; do
        show_menu
        read -p "Enter your choice (1-7): " choice
        
        case $choice in
            1) check_prerequisites ;;
            2) validate_env ;;
            3) build_frontend ;;
            4) test_backend ;;
            5) deploy_frontend ;;
            6) show_checklist ;;
            7) 
                print_success "Goodbye!"
                exit 0
                ;;
            *) 
                print_error "Invalid choice. Please try again."
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
    done
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi