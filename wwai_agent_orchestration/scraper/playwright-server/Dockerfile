FROM mcr.microsoft.com/playwright:v1.57.0-jammy

# Install Playwright browsers (Chromium, Firefox, WebKit)
RUN npx playwright install chromium
RUN npx playwright install-deps chromium

# Expose the Playwright server port
EXPOSE 3099

# Start Playwright driver server on port 3099
# Use --host 0.0.0.0 to allow connections from outside the container
CMD ["npx", "-y", "playwright@1.57.0", "run-server", "--port", "3099", "--host", "0.0.0.0"]