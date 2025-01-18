# =========================================================
# Zsh Configuration File (.zshrc)
# Arch Linux - Customized by KJoo
# =========================================================

# --------------------------------
# Welcome Message
# --------------------------------
echo -e "\n\033[1;36mWelcome to Arch Linux, $USER! Enjoy your session.\033[0m\n"

# --------------------------------
# Environment Variables
# --------------------------------
export PATH=$HOME/bin:$HOME/.local/bin:/usr/local/bin:$PATH
export ZSH="$HOME/.oh-my-zsh"
export TERM="xterm-256color" # Supports 256 colors in terminal

# --------------------------------
# Theme & Prompt
# --------------------------------
ZSH_THEME="powerlevel10k/powerlevel10k"
PROMPT='%F{green}%n@Arch%f %F{blue}%~%f %# '

# Uncomment if using Powerlevel10k and its configuration
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# --------------------------------
# Plugins
# --------------------------------
plugins=(
    git              # Git integration
    zsh-autosuggestions # Suggests commands as you type
    zsh-syntax-highlighting # Adds syntax highlighting
    zsh-completions  # Advanced command completions
    sudo             # Allows running previous commands with `sudo`
)

# Source Oh My Zsh framework
source $ZSH/oh-my-zsh.sh

# --------------------------------
# Source Aliases and Functions
# --------------------------------
[[ -f ~/.zsh_aliases ]] && source ~/.zsh_aliases # Load aliases
[[ -f ~/.zsh_functions ]] && source ~/.zsh_functions # Load functions

# --------------------------------
# Performance Tweaks
# --------------------------------
zstyle ':omz:update' frequency 7        # Auto-update Oh My Zsh every 7 days
ENABLE_CORRECTION="true"                # Enable command auto-correction
DISABLE_UNTRACKED_FILES_DIRTY="true"   # Speed up large Git repositories

# --------------------------------
# Reload Message
# --------------------------------
reload_message() {
    echo -e "\033[1;32mZsh configuration reloaded successfully!\033[0m"
}
trap reload_message EXIT

