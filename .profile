# default umask rw-rw-r--
umask 0002

alias ls='command ls -bCF --color=auto'
alias ll='ls -l'

source <(kubectl completion bash)
