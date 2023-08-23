#!/bin/bash

# Moves each lambda into its own named folder for CloudFormation package command
# Must be run in root directory of repository

fil1=./lambda/
fil2=.py

zip -qr9 function.zip ./components

for lambda in ./lambda/*.py
do
  dir=$(printf '%s' "${lambda//$fil1/}")
  dir=$(printf '%s' "${dir//$fil2/}")

  if [ $dir != "__init__" ]
  then
    cp function.zip $dir.zip
    zip -qr9 $dir.zip $lambda
  fi
done

rm function.zip