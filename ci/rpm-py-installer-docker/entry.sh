#!/bin/bash

echo 'Using system Pythons and ohter Pythons installed by pyenv.'
echo 'List up by "pyenv versions".'
pyenv versions

exec "${@}"
