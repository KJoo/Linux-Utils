# =========================================================
# Zsh Aliases (.zsh_aliases)
# =========================================================

# Editing and Reloading
alias aliases="nvim ~/.zsh_aliases"         # Edit aliases
alias zshrc="nvim ~/.zshrc"                # Edit .zshrc
alias {src,refresh,reload}="source ~/.zshrc" # Reload .zshrc
alias custom="cd $ZSH_CUSTOM"              # Navigate to Oh My Zsh custom folder

# Package Management (Arch + AUR)
alias update="yay -Syu --combinedupgrade --noconfirm" # Update all packages
alias search="search_packages"          # Unified Arch and AUR search
alias install="install_package"         # Install with Arch/AUR checks

# Navigation
alias ..="cd .."                         # Move up one directory
alias home="cd $HOME"                    # Go to home directory
alias config="cd ~/.config/nvim"         # Navigate to Neovim config
alias cproj="cd ~/dev/cpp/projects"      # Navigate to C++ projects
alias pproj="cd ~/dev/python/projects"   # Navigate to Python projects
alias pokemon="cd ~/dev/cpp/projects/pokemon" # Navigate to Pokemon project
alias dev="cd ~/dev"                     # Navigate to development folder
alias {download,downloads,downs,dn,down}="$HOME/Downloads" # Shortcuts to Downloads

# Common Utilities
alias q="exit"                           # Quit terminal
alias cls="clear"                        # Clear terminal
alias {lsa,list}="ls -a"                 # List all files, including hidden ones

# Python Virtual Environment
alias cvenv="python -m venv venv"        # Create virtual environment
alias venv="source venv/bin/activate"    # Activate virtual environment

