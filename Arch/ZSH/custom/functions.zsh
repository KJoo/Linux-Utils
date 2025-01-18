# =========================================================
# Zsh Functions (.zsh_functions)
# =========================================================

# --------------------------------
# Search for packages in Arch and AUR
# --------------------------------
search_packages() {
    echo "Searching Arch repositories:"
    pacman -Ss "$1" | grep "$1"
    echo
    echo "Searching AUR:"
    yay -Ss "$1" | grep "$1"
}

# --------------------------------
# Install packages with Arch/AUR checks
# --------------------------------
install_package() {
    local package="$1"
    local arch_version
    local aur_version

    echo "Checking Arch repositories for '$package':"
    arch_version=$(pacman -Si "$package" 2>/dev/null | grep Version | awk '{print $3}')
    [[ -n "$arch_version" ]] && echo "Arch version available: $arch_version" || echo "No Arch version available."

    echo
    echo "Checking AUR for '$package':"
    aur_version=$(yay -Si "$package" 2>/dev/null | grep Version | awk '{print $3}')
    [[ -n "$aur_version" ]] && echo "AUR version available: $aur_version" || echo "No AUR version available."

    if [[ -n "$arch_version" && -n "$aur_version" ]]; then
        echo "1. Install Arch version ($arch_version)"
        echo "2. Install AUR version ($aur_version)"
        read -rp "Choose an option (1 or 2): " choice
        [[ "$choice" == "1" ]] && sudo pacman -S "$package" || yay -S "$package"
    elif [[ -n "$arch_version" ]]; then
        sudo pacman -S "$package"
    elif [[ -n "$aur_version" ]]; then
        yay -S "$package"
    else
        echo "Package '$package' not found."
    fi
}

# --------------------------------
# Extract files from various archive formats
# --------------------------------
extract() {
    if [[ -f $1 ]]; then
        case $1 in
            *.tar.bz2) tar xvjf "$1" ;;
            *.tar.gz) tar xvzf "$1" ;;
            *.zip) unzip "$1" ;;
            *.7z) 7z x "$1" ;;
            *.rar) unrar x "$1" ;;
            *) echo "Cannot extract '$1' (unsupported format)" ;;
        esac
    else
        echo "File '$1' does not exist."
    fi
}

