#!/bin/bash
# Installation script for Meshcore Firmware Editor and Flasher (Linux/macOS)

# Don't use set -e here, as we want to continue even if optional dependencies fail

echo "=========================================="
echo "Meshcore Firmware Editor and Flasher - Installation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
echo "Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python found: $PYTHON_VERSION"
    PYTHON_CMD=python3
elif command_exists python; then
    PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python found: $PYTHON_VERSION"
    PYTHON_CMD=python
else
    echo -e "${RED}✗${NC} Python not found!"
    echo "Please install Python 3.6 or higher from https://www.python.org/downloads/"
    exit 1
fi

# Check Python version
PYTHON_VER=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VER | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VER | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 6 ]); then
    echo -e "${RED}✗${NC} Python 3.6 or higher is required (found $PYTHON_VER)"
    exit 1
fi

# Check pip
echo ""
echo "Checking pip installation..."
if command_exists pip3; then
    echo -e "${GREEN}✓${NC} pip3 found"
    PIP_CMD=pip3
elif command_exists pip; then
    echo -e "${GREEN}✓${NC} pip found"
    PIP_CMD=pip
else
    echo -e "${YELLOW}⚠${NC} pip not found, installing..."
    $PYTHON_CMD -m ensurepip --upgrade || {
        echo -e "${RED}✗${NC} Failed to install pip. Please install pip manually."
        exit 1
    }
    PIP_CMD="$PYTHON_CMD -m pip"
fi

# Check Tkinter
echo ""
echo "Checking Tkinter..."
if $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Tkinter is available"
else
    echo -e "${YELLOW}⚠${NC} Tkinter not found"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "Installing Tkinter for Linux..."
        if command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y python3-tk
        elif command_exists dnf; then
            sudo dnf install -y python3-tkinter
        elif command_exists pacman; then
            sudo pacman -S --noconfirm tk
        elif command_exists zypper; then
            sudo zypper install -y python3-tk
        else
            echo -e "${YELLOW}⚠${NC} Please install python3-tk using your package manager"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing Tkinter for macOS..."
        if command_exists brew; then
            brew install python-tk
        else
            echo -e "${YELLOW}⚠${NC} Please install python-tk: brew install python-tk"
        fi
    fi
fi

# Install the package
echo ""
echo "Installing Meshcore Firmware Editor and Flasher..."
if ! $PIP_CMD install -e . --user; then
    echo -e "${RED}✗${NC} Installation failed!"
    exit 1
fi

echo ""
echo -e "${GREEN}=========================================="
echo -e "Main installation completed successfully!"
echo -e "==========================================${NC}"
echo ""

# Install optional dependencies
echo ""
echo "Installing optional dependencies..."
echo ""

# Install PlatformIO
echo "Installing PlatformIO..."
if command_exists pio; then
    PIO_VERSION=$(pio --version 2>&1 | head -n1)
    echo -e "${GREEN}✓${NC} PlatformIO already installed: $PIO_VERSION"
else
    echo "Installing PlatformIO via pip..."
    if $PIP_CMD install platformio --user; then
        # Add user's local bin to PATH if not already there
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            echo ""
            echo -e "${YELLOW}⚠${NC} Note: You may need to add ~/.local/bin to your PATH"
            echo "  Add this to your ~/.bashrc or ~/.zshrc:"
            echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
            echo ""
        fi
        if command_exists pio; then
            PIO_VERSION=$(pio --version 2>&1 | head -n1)
            echo -e "${GREEN}✓${NC} PlatformIO installed: $PIO_VERSION"
        else
            echo -e "${YELLOW}⚠${NC} PlatformIO installed but 'pio' command not found in PATH"
            echo "  You may need to restart your terminal or add ~/.local/bin to PATH"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Failed to install PlatformIO. You can install it manually:"
        echo "  $PIP_CMD install platformio"
    fi
fi

# Install Git
echo ""
echo "Installing Git..."
if command_exists git; then
    GIT_VERSION=$(git --version)
    echo -e "${GREEN}✓${NC} Git already installed: $GIT_VERSION"
else
    echo "Installing Git..."
    GIT_INSTALLED=false
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt-get; then
            if sudo apt-get update && sudo apt-get install -y git; then
                GIT_INSTALLED=true
            fi
        elif command_exists dnf; then
            if sudo dnf install -y git; then
                GIT_INSTALLED=true
            fi
        elif command_exists pacman; then
            if sudo pacman -S --noconfirm git; then
                GIT_INSTALLED=true
            fi
        elif command_exists zypper; then
            if sudo zypper install -y git; then
                GIT_INSTALLED=true
            fi
        else
            echo -e "${YELLOW}⚠${NC} Please install git using your package manager"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command_exists brew; then
            if brew install git; then
                GIT_INSTALLED=true
            fi
        else
            echo -e "${YELLOW}⚠${NC} Homebrew not found. Installing Git..."
            echo "  Please install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "  Then run: brew install git"
        fi
    fi
    
    if [ "$GIT_INSTALLED" = true ] && command_exists git; then
        GIT_VERSION=$(git --version)
        echo -e "${GREEN}✓${NC} Git installed: $GIT_VERSION"
    else
        echo -e "${YELLOW}⚠${NC} Git installation may require manual steps"
    fi
fi

echo ""
echo -e "${GREEN}=========================================="
echo -e "Installation completed!"
echo -e "==========================================${NC}"
echo ""
echo "You can now run the application with:"
echo "  meshcore-firmware-editor"
echo ""
echo "Or directly with:"
echo "  $PYTHON_CMD meshcore_flasher.py"
echo ""

