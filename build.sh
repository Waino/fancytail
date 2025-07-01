#!/bin/bash

set -eux

# Update the bash completion
_FANCYTAIL_COMPLETE=bash_source fancytail > fancytail/fancytail.bash-completion

# Build the package
flit build
