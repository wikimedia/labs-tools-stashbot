# default umask rw-rw-r--
umask 0002

alias ls='command ls -bCF --color=auto'
alias ll='ls -l'

LESS=-FiQRwX
export LESS

which kubectl >/dev/null 2>&1 && source <(kubectl completion bash)
