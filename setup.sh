#!/bin/bash -i

terminalWidth=$(tput cols)
if [ -z "$terminalWidth" ]; then
    terminalWidth=80
fi

function printGreen() {
    printf "\e[32m$1\e[0m\n"
}

function printRed() {
    printf "\e[31m$1\e[0m\n"
}

function printYellow() {
    printf "\e[33m$1\e[0m\n"
}

function centerText() {
    textLength=${#1}
    spaces=$((terminalWidth-textLength-2))
    leftSpaces=$((spaces/2))
    rightSpaces=$((spaces-leftSpaces+2))

    printf "\e[36m│\e[0m"
    for ((i=1; i < $leftSpaces; i++)); do
        printf " "
    done
    if [ "$3" = true ]; then
        printf "\e[1;${2}m$1\e[0m"
    else
        printf "\e[${2}m$1\e[0m"
    fi
    for ((i=1; i < $rightSpaces; i++)); do
        printf " "
    done
    printf "\e[36m│\e[0m\n"
}

function spaces() {
    printf "\e[36m│\e[0m" 
    for ((j=1; j < $terminalWidth - 1; j++)); do
        printf " "
    done
    printf "\e[36m│\e[0m\n"
}

function topBorder() {
    printf "\e[36m┌"
    for ((i=1; i < $terminalWidth - 1; i++)); do
        printf "─"
    done
    printf "┐\e[0m\n"
}

function bottomBorder() {
    printf "\e[36m└"
    for ((i=1; i < $terminalWidth - 1; i++)); do
        printf "─"
    done
    printf "┘\e[0m\n"
}

function ubuntuOrDebian() {
    if [[ "$(cat /etc/*-release | grep ^ID=)" == "ID=ubuntu" || "$(cat /etc/*-release | grep ^ID=)" == "ID=debian" ]]; then
        return 0
    else
        return 1
    fi
}

clear

topBorder
spaces
spaces
spaces
centerText "Home Api" "32" true
spaces
centerText "Welcome to the setup script for the project" "95"
spaces
spaces
spaces
bottomBorder

printf "\n\e[33mThis script will install python3, and pip3.\nDo you wish to continue?\e[0m" -n
read -p " (y/n): " yn

case $yn in
    [Yy]* ) ;;
    [Nn]* ) exit;;
    * ) echo "Please answer yes or no.";;
esac

if which python3 >/dev/null ; then
    printGreen "python3 is already installed."
else
    printYellow "Installing python3."
    
    if [ -x "$(command -v apt-get)" ]; then
        sudo apt-get install python3 -y
    elif [ -x "$(command -v pacman)" ]; then
        sudo pacman -S python3
    elif [ -x "$(command -v pkg)" ]; then
        sudo pkg install python3
    elif [ -x "$(command -v brew)" ]; then
        sudo brew install python3
    else
        printRed "Unable to determine package manager for this system"
        exit 1
    fi

    printGreen "python3 is installed."
fi

function checkPip3() {
    if which pip3 >/dev/null ; then
        printGreen "pip3 is already installed."
        return 0
    elif which ~/.local/bin/pip3 >/dev/null ; then
        printGreen "pip3 is already installed."
        printYellow "adding ~/.local/bin to PATH"

        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            if cat ~/.bashrc | grep "# LOCAL_BIN_PATH" > /dev/null ; then
                printGreen "LOCAL_BIN_PATH is already in .bashrc"
                source ~/.bashrc
            else
                printYellow "adding LOCAL_BIN_PATH to .bashrc"
                echo "" >> ~/.bashrc
                echo "# LOCAL_BIN_PATH" >> ~/.bashrc
                echo "export PATH=\$PATH:\$HOME/.local/bin" >> ~/.bashrc
                source ~/.bashrc
            fi
        fi
        return 0
    else 
        return 1
    fi
}

if checkPip3 ; then
    printGreen "pip3 is already installed."
    printYellow "adding ~/.local/bin to PATH"

    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        if cat ~/.bashrc | grep "# LOCAL_BIN_PATH" > /dev/null ; then
            printGreen "LOCAL_BIN_PATH is already in .bashrc"
            source ~/.bashrc
        else
            printYellow "adding LOCAL_BIN_PATH to .bashrc"
            echo "" >> ~/.bashrc
            echo "# LOCAL_BIN_PATH" >> ~/.bashrc
            echo "export PATH=\$PATH:\$HOME/.local/bin" >> ~/.bashrc
            source ~/.bashrc
        fi
    fi
else
    printYellow "Installing pip3."

    if which curl >/dev/null ; then
        printYellow "Downloading via curl."
        curl -fsSL https://bootstrap.pypa.io/get-pip.py | python3 -
    elif which wget >/dev/null ; then
        printYellow "Downloading via wget."
        wget -qO- https://bootstrap.pypa.io/get-pip.py | python3 -
    else
        printRed "Cannot download, neither wget nor curl is available."
        exit 1
    fi

    if checkPip3 ; then
        printGreen "pip3 is installed."
    else
        printRed "failed to install pip3."
        printRed "Please install pip3 manually."
        exit 1
    fi
fi

pip3 install -r requirements.txt

printYellow "Generating api-key secret"

SECRET=$(python3 -c "import os; import binascii; print(binascii.hexlify(os.urandom(32)))")
ALGORITHM="HS256"
substring=$(echo "$SECRET" | sed "s/'//g" | awk '{print $1}' | cut -c 2-)

if [[ -f .env ]]; then
    printGreen ".env exists, skipping."
else
    printYellow ".env does not exist, creating it."
    echo "secret=$substring" > .env
    echo "algorithm=$ALGORITHM" >> .env
    echo "port=8000" >> .env
fi

printGreen "api-key secret is generated."