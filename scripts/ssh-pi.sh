#!/bin/bash
# SSH helper for Skylapse Pi
# Usage: ./scripts/ssh-pi.sh "command"
# Or: ./scripts/ssh-pi.sh (for interactive shell)

PI_USER="nicholasmparker"
PI_HOST="helios.local"

if [ $# -eq 0 ]; then
    # No arguments - interactive shell
    ssh ${PI_USER}@${PI_HOST}
else
    # Run command
    ssh ${PI_USER}@${PI_HOST} "$@"
fi
