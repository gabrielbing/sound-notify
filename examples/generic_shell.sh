#!/bin/bash
# Generic shell script example for any AI Agent
# This script shows how to integrate sound-notify into any system that can run shell commands

SOUND_NOTIFY_PATH="/path/to/sound-notify/scripts/notify.py"

# Function to notify task completion
notify_done() {
    python "$SOUND_NOTIFY_PATH" done --edge
}

# Function to notify need for confirmation
notify_confirm() {
    python "$SOUND_NOTIFY_PATH" confirm --edge
}

# Function to notify permission request
notify_perm() {
    python "$SOUND_NOTIFY_PATH" perm --edge
}

# Function to notify alert
notify_alert() {
    python "$SOUND_NOTIFY_PATH" alert --edge
}

# Function to notify daily briefing
notify_daily() {
    python "$SOUND_NOTIFY_PATH" daily --edge
}

# Function to notify thinking/processing
notify_thinking() {
    python "$SOUND_NOTIFY_PATH" thinking --edge
}

# Example usage in your Agent's hook/trigger system:
# 
# After task completion:
#   notify_done
#
# Before asking for confirmation:
#   notify_confirm
#
# Before requesting permissions:
#   notify_perm
#

# Uncomment to test all notifications:
# python "$SOUND_NOTIFY_PATH" test --edge
