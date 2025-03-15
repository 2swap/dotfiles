#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '
alias gpt='~/gpt.py'
alias teach='~/teach.py'
alias st='cd ~/swaptube && tmux'
alias listen='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py -l'
alias huion='xinput map-to-output "HID 256c:006d Pen Pen (0)" "HDMI-0"'
neofetch
