#!/bin/bash

# DWM3001CDK Demo Firmware - Python Environment Setup Script
# This script creates a virtual environment and installs dependencies

set -e  # Exit on any error

# Configuration
VENV_NAME="venv"
PYTHON_CMD="python3"
REQUIREMENTS_FILE="requirements.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Main setup function
main() {
    print_status "DWM3001CDK Python Environment Setup"
    echo "======================================"

    # Check if Python is available
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "$PYTHON_CMD is not installed or not in PATH"
        exit 1
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    print_status "Using $PYTHON_VERSION"

    # Check if virtual environment directory exists
    if [[ -d "$VENV_NAME" ]]; then
        print_status "Virtual environment '$VENV_NAME' already exists"
    else
        # Create new virtual environment
        print_status "Creating virtual environment '$VENV_NAME'..."
        $PYTHON_CMD -m venv "$VENV_NAME"
        print_success "Virtual environment created"
    fi

    # Upgrade pip in the virtual environment
    print_status "Upgrading pip in virtual environment..."
    "$VENV_NAME/bin/python" -m pip install --upgrade pip

    # Install requirements if requirements.txt exists
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        print_status "Installing dependencies from $REQUIREMENTS_FILE..."
        "$VENV_NAME/bin/python" -m pip install -r "$REQUIREMENTS_FILE"
        print_success "Dependencies installed successfully"
    else
        print_warning "$REQUIREMENTS_FILE not found"
        print_status "Installing basic dependencies..."
        "$VENV_NAME/bin/python" -m pip install pyserial
        print_success "Basic dependencies installed"
    fi

    # Display success message and instructions
    echo ""
    print_success "Setup completed successfully!"
    echo ""
    echo "======================================"
    echo "To use the environment:"
    echo ""
    echo "1. Activate the virtual environment:"
    echo "   source $VENV_NAME/bin/activate"
    echo ""
    echo "2. Test the serial collector:"
    echo "   python serial_collector.py --list-devices"
    echo ""
    echo "3. Deactivate when done:"
    echo "   deactivate"
    echo "======================================"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --clean, -c    Remove existing virtual environment before setup"
        echo ""
        echo "This script will:"
        echo "  1. Create a Python virtual environment if it doesn't exist"
        echo "  2. Install required dependencies"
        echo ""
        exit 0
        ;;
    --clean|-c)
        if [[ -d "$VENV_NAME" ]]; then
            print_status "Removing existing virtual environment..."
            rm -rf "$VENV_NAME"
            print_success "Virtual environment removed"
        fi
        main
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac