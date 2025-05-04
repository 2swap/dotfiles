#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '
alias chat='~/dotfiles/contents/ai_tools.py chat'
alias teach='~/dotfiles/contents/ai_tools.py teach'
alias vocab='~/dotfiles/contents/ai_tools.py vocab'
alias rw='~/dotfiles/contents/ai_tools.py rw'
alias au='~/dotfiles/contents/toggle_audio.sh'
alias st='cd ~/swaptube && tmux'
alias listen='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py -l'
alias watch='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py'
alias huion='xinput map-to-output "HID 256c:006d Pen Pen (0)" "HDMI-0"'
neofetch
export PYTHONHISTFILE=/dev/null
