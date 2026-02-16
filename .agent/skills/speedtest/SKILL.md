---
name: Speedtest Capture
description: Launches the Speedtest app and takes a screenshot after a specified delay.
---

# Speedtest Capture Skill

This skill allows the agent to measure internet speed using the native macOS Speedtest app and capture the result.

## Capabilities
1. **Launch Speedtest**: Opens the Speedtest application.
2. **Delayed Screenshot**: Waits for a specified number of seconds (to allow the test to complete) and takes a screenshot.
3. **Automatic Upload**: Returns the `UPLOAD:` command for Satele to send the image back to the user.

## Tools
The agent can use the following script:
`python3 .agent/skills/speedtest/speedtest_capture.py`

### Usage
- Runs a complete internet speed test using speedtest-cli
- Generates a visual result image with ping, download, and upload speeds
- Fully automated - no manual interaction required
- Takes approximately 30-60 seconds to complete

## Example
If a user says "measure speed", the agent should:
1. Run `python3 .agent/skills/speedtest/speedtest_capture.py`
2. Get the output `UPLOAD:/path/to/speedtest.png`
3. Reply with that string.
