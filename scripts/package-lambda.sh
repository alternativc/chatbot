#!/bin/bash

set -Eeo pipefail

# Relative path to the lambda directory
LAMBDA_ROOT_DIR="../lambda"

# Loop over each service in the lambda directory
for service in $(ls $LAMBDA_ROOT_DIR); do

    echo "Packaging for ${service} started!"

    # Navigate to service directory
    pushd $LAMBDA_ROOT_DIR/$service

    # Create virtual environment
    python3 -m venv venv

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    pip install -q -r requirements.txt

    # Deactivate virtual environment
    deactivate

    # Create a package directory if it doesn't exist
    mkdir -p package

    # Package the Lambda function and its dependencies into a zip
    # Including python libraries from venv and your lambda code
    zip -q -r9 package/${service}.zip . -x "venv/*" "requirements.txt" "package/*"
    pushd venv/lib/python3.*/site-packages/
    zip -q -r9 ../../../../package/${service}.zip .
    popd

    # Clean up: remove the virtual environment
    rm -rf venv

    # Return to the scripts directory before processing the next service
    popd
    echo "Packaging for ${service} completed!"
done


