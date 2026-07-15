#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '
alias chat='~/dotfiles/contents/ai_tools/chat.py'
alias vocab='~/dotfiles/contents/ai_tools/vocab.py'
alias study='~/dotfiles/contents/ai_tools/study.py'
alias quiz='~/dotfiles/contents/ai_tools/quiz.py'
alias rw='~/dotfiles/contents/ai_tools/rw.py'
alias au='~/dotfiles/contents/toggle_audio.sh'
alias st='cd ~/swaptube && tmux'
alias listen='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py -l'
alias watcher='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py'
neofetch
export PYTHONHISTFILE=/dev/null
alias mountprimary='sudo mount -t nfs 192.168.1.11:/run/media/2swap/primary ~/mnt/primary'

# The next line updates PATH for the Google Cloud SDK.
if [ -f '/home/2swap/Downloads/google-cloud-sdk/path.bash.inc' ]; then . '/home/2swap/Downloads/google-cloud-sdk/path.bash.inc'; fi

# The next line enables shell command completion for gcloud.
if [ -f '/home/2swap/Downloads/google-cloud-sdk/completion.bash.inc' ]; then . '/home/2swap/Downloads/google-cloud-sdk/completion.bash.inc'; fi
