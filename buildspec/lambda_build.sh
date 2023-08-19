#!/bin/bash

# Moves each lambda into its own named folder for CloudFormation package command
# Must be run in root directory of repository

fil1=./lambda/
fil2=.py

for lambda in ./lambda/*.py
do
  dir=$(printf '%s' "${lambda//$fil1/}")
  dir=$(printf '%s' "${dir//$fil2/}")

  if [ "$dir" != "__init__" ]
  then
    mkdir "$dir" "$dir"/lambda
    mv "$lambda" "$dir"/"$lambda"
    cp ./components "$dir"/components -r
  fi
done