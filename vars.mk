# Makefile variables file.
#
# Variables shared across project Makefiles via 'include vars.mk'.
#
# - ./Makefile

# Shell settings
SHELL := /bin/bash

# Environment settings
ENV ?= dev

# Project settings
PROJECT_NAME := test-shiny-app

# Python settings
PYTHON ?= $(shell command -v python || command -v python3)
UV ?= uv
# uv defaults virtual environment to `$VIRTUAL_ENV` if set; otherwise .venv
VIRTUAL_ENV ?= .venv

UV_LOCK := uv.lock

# SWAGGER_FILE :=
