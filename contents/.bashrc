#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '
alias gpt='~/dotfiles/contents/gpt.py'
alias au='~/dotfiles/contents/toggle_audio.sh'
alias teach='~/dotfiles/contents/teach.py'
alias rw='~/dotfiles/contents/refactor.py'
alias st='cd ~/swaptube && tmux'
alias listen='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py -l'
alias watch='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py'
alias indo='~/dotfiles/contents/vocab.py Indonesian'
alias tur='~/dotfiles/contents/vocab.py Turkish'
alias huion='xinput map-to-output "HID 256c:006d Pen Pen (0)" "HDMI-0"'
neofetch
