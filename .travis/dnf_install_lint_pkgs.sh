#!/bin/sh
# shellcheck disable=SC2039

if [[ "${TOXENV}" = "" || "${TOXENV}" =~ "lint" ]]; then
    # Used in scripts/lint_bash.sh
    dnf -y install \
        which \
        /usr/bin/find \
        ShellCheck
else
    echo "Nothing to do."
fi
