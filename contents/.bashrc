#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '
alias chat='~/dotfiles/contents/ai_tools.py chat'
alias debug='~/dotfiles/contents/ai_tools.py debug'
alias teach='~/dotfiles/contents/ai_tools.py teach'
alias span='~/dotfiles/contents/ai_tools.py vocab -f Spanish -b English'
alias indo='~/dotfiles/contents/ai_tools.py vocab -f Indonesian -b Spanish'
alias telugu='~/dotfiles/contents/ai_tools.py vocab_easy -f Telugu -b Indonesian'
alias hindi='~/dotfiles/contents/ai_tools.py vocab_easy -f Hindi -b Indonesian'
alias french='~/dotfiles/contents/ai_tools.py vocab -f French -b Indonesian'
alias turkish='~/dotfiles/contents/ai_tools.py vocab_easy -f Turkish -b Indonesian'
alias chinese='~/dotfiles/contents/ai_tools.py vocab -f Chinese -b Indonesian'
alias vocabfile='~/dotfiles/contents/ai_tools.py vocabfile'
alias rw='~/dotfiles/contents/ai_tools.py rw'
alias au='~/dotfiles/contents/toggle_audio.sh'
alias st='cd ~/swaptube && tmux'
alias listen='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py -l'
alias watcher='cd /run/media/2swap/primary/immersion-tools/watcher && ./watcher.py'
neofetch
export PYTHONHISTFILE=/dev/null
alias mountprimary='sudo mount -t nfs 192.168.1.11:/run/media/2swap/primary ~/mnt/primary'
