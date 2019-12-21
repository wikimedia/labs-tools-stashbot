# default umask rw-rw-r--
umask 0002

alias ls='command ls -bCF --color=auto'
alias ll='ls -l'

LESS=-FiQRwX
export LESS

alias kubectl=/usr/bin/kubectl
source <(kubectl completion bash)
