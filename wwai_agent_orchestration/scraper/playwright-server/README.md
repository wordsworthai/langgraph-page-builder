# Build the Docker image
docker build -t playwright-run-server-simple .

# Remove existing container if it exists
docker rm -f pw-server 2>/dev/null

# Run the Playwright server container
docker run -d --name pw-server \
  -p 3099:3099 \
  playwright-run-server-simple

# Check if the server is running
docker logs pw-server

# To stop the server
# docker stop pw-server

# To restart the server
# docker start pw-server
